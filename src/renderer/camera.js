// One transform on the chess parent; sprite animations retain their own transforms.
const CAMERA_FOLLOW = "CAMERA_FOLLOW";
const CAMERA_PUSH = "CAMERA_PUSH";
const CAMERA_PULL = "CAMERA_PULL";
const CAMERA_FOCUS = "CAMERA_FOCUS";
const CAMERA_PAN = "CAMERA_PAN";
const CAMERA_RESET = "CAMERA_RESET";

const camera = {
    animation: null,
    revision: 0,
    finished: Promise.resolve(),
    identity: {x: 0, y: 0, zoom: cameraConfig.wideZoom, rotation: 0},
    // Commanded absolute target, not the interpolated on-screen pose. Transient
    // motion never writes this value or this element's transform.
    pose: {x: 0, y: 0, zoom: cameraConfig.wideZoom, rotation: 0},

    transform(pose) {
        return "translate(" + pose.x + "px," + pose.y + "px) rotate(" +
            pose.rotation + "deg) scale(" + pose.zoom + ")";
    },

    target(square, dramatic = false) {
        return camera_focus_destination(square, dramatic ? "L" : "K");
    },

    bounded(pose) {
        const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
        return {
            x: clamp(pose.x, -cameraConfig.maxTranslation, cameraConfig.maxTranslation),
            y: clamp(pose.y, -cameraConfig.maxTranslation, cameraConfig.maxTranslation),
            zoom: clamp(pose.zoom, 1, cameraConfig.maxZoom),
            rotation: clamp(pose.rotation, -cameraConfig.maxRotation, cameraConfig.maxRotation)
        };
    },

    // Capture the displayed pose before replacing an in-flight animation: no jump.
    to(pose, duration = cameraConfig.duration) {
        if (!cameraConfig.enabled) return Promise.resolve();
        this.revision++;
        const from = getComputedStyle(board).transform;
        if (this.animation) this.animation.cancel();
        this.pose = this.bounded({...this.identity, ...pose});
        const target = this.transform(this.pose);
        board.style.transform = target;
        if (duration <= 0) {
            this.animation = null;
            this.finished = Promise.resolve();
            return this.finished;
        }
        const animation = board.animate([{transform: from}, {transform: target}], {
            duration, easing: cameraConfig.easing, fill: "both"
        });
        this.animation = animation;
        this.finished = animation.finished.catch(error => {
            if (error.name !== "AbortError") throw error;
        }).finally(() => {
            if (this.animation === animation) {
                animation.cancel();
                this.animation = null;
            }
        });
        return this.finished;
    },

    // Immediate initialization/replay reset; animated reset is camera_reset().
    reset() {
        this.revision++;
        if (this.animation) this.animation.cancel();
        this.animation = null;
        this.pose = {...this.identity};
        board.style.transform = this.transform(this.identity);
        board.style.transformOrigin = "center center";
        this.finished = Promise.resolve();
    },

    directMove(move) {
        if (!cameraConfig.enabled || !move.camera_directive) return this.finished;
        if (move.camera_directive === "J") return camera_reset();
        return this.to(camera_focus_destination(move.to, move.camera_directive),
                       cameraConfig.shots[move.camera_directive].duration);
    },

    apply(preset, from, to) {
        switch (preset) {
            case CAMERA_FOLLOW: return camera_follow_move(from, to);
            case CAMERA_PUSH: return camera_push(to);
            case CAMERA_FOCUS: return camera_focus(to);
            case CAMERA_PAN: return camera_pan(from, to);
            case CAMERA_PULL: return camera_pull_back();
            case CAMERA_RESET: return camera_reset();
            default: throw new Error("Unknown camera preset: " + preset);
        }
    }
};

function camera_follow_move(from_square, to_square) {
    return camera.to(camera_frame_move(from_square, to_square));
}
function camera_focus(square) { return camera.to(camera.target(square)); }
function camera_push(square) { return camera.to(camera.target(square, true), cameraConfig.shots.L.duration); }
function camera_pull_back() { return camera.to(camera.identity, cameraConfig.wideDuration); }
function camera_reset() { return camera.to(camera.identity, cameraConfig.wideDuration); }
async function camera_pan(square_a, square_b) {
    const first = camera_focus(square_a);
    const revision = camera.revision;
    await first;
    if (revision === camera.revision) return camera_focus(square_b);
}

// Shift a local neighborhood inward at edges so it contains actual board context.
function destination_region(square, shot_type) {
    const shot = cameraConfig.shots[shot_type];
    if (!shot) throw new Error("Unknown camera shot: " + shot_type);
    const point=squareToCoords(square), half=squareSize*4;
    const span=Math.min(squareSize*8,shot.region*squareSize);
    const start=index=>Math.max(-half,Math.min(half-span,(index+0.5)*squareSize-half-span/2));
    const left=start(point.x), top=start(point.y);
    return {left, right:left+span, top, bottom:top+span};
}

// Absolute destination shot. Source and travel distance intentionally play no role.
function camera_focus_destination(destination_square, shot_type = "K") {
    const shot = cameraConfig.shots[shot_type];
    const region = destination_region(destination_square, shot_type);
    const point = squareToCoords(destination_square);
    const direction = point.x < 3.5 ? -1 : 1;
    const rotation = direction * Math.min(shot.rotation, cameraConfig.maxRotation);
    const angle = rotation * Math.PI / 180;
    const corners = [region.left, region.right].flatMap(x =>
        [region.top, region.bottom].map(y => ({
            x:x*Math.cos(angle)-y*Math.sin(angle),
            y:x*Math.sin(angle)+y*Math.cos(angle)
        })));
    const xs=corners.map(p=>p.x), ys=corners.map(p=>p.y);
    const minX=Math.min(...xs), maxX=Math.max(...xs);
    const minY=Math.min(...ys), maxY=Math.max(...ys);
    // Reserve room for simultaneous bounded transient transforms. LEGACY has a
    // zero margin and therefore preserves the previous destination framing.
    const limit=cameraConfig.viewportSize/2 - (cameraConfig.transient?.framingMargin || 0);
    // Bound zoom by both the rotated box size and available translation.
    let zoom=Math.min(shot.zoom, cameraConfig.maxZoom,
        2*limit/(maxX-minX), 2*limit/(maxY-minY));
    for (const value of [minX,maxX,minY,maxY]) {
        if (value) zoom=Math.min(zoom,(limit+cameraConfig.maxTranslation)/Math.abs(value));
    }
    // Conservative fallback for an oversized configured neighborhood.
    if (zoom < cameraConfig.wideZoom) return {...camera.identity};
    const center = (lo,hi) => {
        const ideal=-(lo+hi)*zoom/2;
        const lower=Math.max(-cameraConfig.maxTranslation,-limit-lo*zoom);
        const upper=Math.min(cameraConfig.maxTranslation,limit-hi*zoom);
        return Math.max(lower,Math.min(upper,ideal));
    };
    return {x:center(minX,maxX),y:center(minY,maxY),zoom,rotation};
}

// Compatibility for callers; a long path no longer restricts the shot.
function camera_frame_move(from_square, to_square, shot_type = "K") {
    return camera_focus_destination(to_square, shot_type);
}
