// Child media layers own their lifetime, never chess/camera transforms.
// Off mode creates no media nodes, animation clocks, listeners or RAF loops.
const pieceMemeSystem = {
    media: new Map(), active: new Set(), ready: null, loaded: false, audioActive: false,
    debug(key, event, extra = {}) {
        if (!window.PIECE_MEME_DEBUG && !new URLSearchParams(location.search).has('pieceMemeDebug')) return;
        const media = this.media.get(key), config = pieceMemeConfig.entries[key];
        if (!media) return;
        const record = {event, triggerTime:performance.now(), id:config.id, element:key,
            src:media.currentSrc || media.src, audioRequested:config.audio,
            muted:media.muted, mutedAttribute:media.hasAttribute('muted'), volume:media.volume,
            paused:media.paused, currentTime:media.currentTime, readyState:media.readyState,
            connected:media.isConnected, sameVisibleElement:media.closest('.piece-meme')?.firstElementChild===media,
            ...extra};
        (window.pieceMemeDiagnostics ||= []).push(record);
        console.debug('[piece-meme]', record);
    },
    prepare() {
        if (!pieceMemeConfig.enabled) return Promise.resolve();
        if (this.ready) return this.ready;
        this.ready = Promise.all(Object.entries(pieceMemeConfig.entries).map(([key, config]) => {
            if (config.remove) return Promise.resolve();
            const node = document.createElement(config.type === 'video' ? 'video' : 'img');
            node.className = 'piece-meme-media';
            node.draggable = false;
            if (config.type === 'video') {
                node.muted = true; node.defaultMuted = true; node.playsInline = true;
                node.controls = false; node.loop = config.loop; node.preload = 'auto';
            } else node.alt = '';
            this.media.set(key, node);
            if (config.type === 'video') {
                for (const event of ['playing','pause','waiting','seeking','seeked','volumechange','ended'])
                    node.addEventListener(event,()=>this.debug(key,event));
            }
            return new Promise((resolve, reject) => {
                const event = config.type === 'video' ? 'loadeddata' : 'load';
                const cleanup = () => {clearTimeout(timeout);node.removeEventListener(event, loaded);node.removeEventListener('error', failed);};
                const failed = () => {cleanup();reject(Error('Cannot load piece meme '+config.id+': '+config.src));};
                const loaded = () => {cleanup();resolve();};
                const timeout = setTimeout(failed, 15000);
                node.addEventListener(event, loaded, {once:true});
                node.addEventListener('error', failed, {once:true});
                node.src = config.src;
                if (config.type === 'video') node.load();
            });
        })).then(()=>{this.loaded=true;});
        // Exports/playback await the same rejecting promise with a clear asset error.
        this.ready.catch(()=>{});
        return this.ready;
    },
    setMuted(media, muted) {
        // Keep the reflected HTML default and the live state in agreement.
        // In particular, never insert an audible video carrying a muted attribute.
        media.defaultMuted = muted;
        media.muted = muted;
    },
    unlockAudio() {
        // Called synchronously in the Play gesture, before any await. Prime only
        // opted-in elements unmuted at zero volume, without audible pre-roll.
        return Promise.all(Object.entries(pieceMemeConfig.entries).map(async ([key, config]) => {
            if (!config.audio || config.type !== 'video') return;
            const media = this.media.get(key);
            if (!media) return;
            media.pause(); media.volume = 0; this.setMuted(media, false);
            try { await media.play(); this.debug(key, "unlock-resolved"); }
            catch (error) { this.debug(key,'unlock-rejected',{error:error.name}); console.warn('Could not unlock piece meme audio:', error); }
            finally { media.pause(); media.currentTime = 0; this.setMuted(media, true); media.volume = 1; }
        }));
    },
    initialize() {
        if (!this.loaded || !pieceMemeConfig.initial) return;
        for (const key of pieceMemeConfig.initial) {
            const config = pieceMemeConfig.entries[key];
            const actor = pieceBySquare[config.target];
            if (actor) this.attach(actor, key, config);
        }
    },
    bind(move, schedule, actor) {
        if (!pieceMemeConfig.enabled) return () => {};
        const keys = Array.isArray(move.piece_meme) ? move.piece_meme : [move.piece_meme];
        return schedule.onCue(event => {
            for (const key of keys) {
                const config = pieceMemeConfig.entries[key];
                if (!config || event.cue !== (config.when === 'start' ? 'launch' : 'settled')) continue;
                // Settled fires before the moving actor is inserted at its destination.
                // Captured actors have already left the occupancy map by this cue.
                const target = !config.target ? actor
                    : event.cue === 'settled' && config.target === move.to ? actor
                    : pieceBySquare[config.target];
                if (target) {
                    if (config.remove) this.removeActor(target);
                    else this.attach(target, key, config);
                }
            }
        });
    },
    attach(actor, key, config) {
        this.removeActor(actor);
        const symbol = (actor.sprite.src.split('/').pop() || '')[1];
        const kind = {P:'pawn',N:'knight',B:'bishop',R:'rook',Q:'queen',K:'king'}[symbol];
        config = {...config, ...pieceMemeConfig.anchors?.[kind], ...config.placement};
        const media = this.media.get(key);
        if (!media || !actor.isConnected) return;
        const host = actor.reaction;
        host.classList.add('piece-meme-host');
        const layer = document.createElement('div');
        layer.className = 'piece-meme piece-meme-'+config.shape;
        layer.dataset.memeId = config.id;
        layer.style.transform = 'translate(-50%,-50%) translate('+config.x+'px,'+config.y+'px) scale('+config.scale+')';
        if (config.type === 'video') {
            this.setMuted(media, !(config.audio && this.audioActive));
            media.volume = 1;
        }
        layer.appendChild(media); host.appendChild(layer);
        const clock = layer.animate([{opacity:1},{opacity:1}], {duration:config.hold ? Infinity : config.dur*1000,fill:'both'});
        const entry = {key,actor,host,layer,media,clock,hold:config.hold,frame:null,closed:false,playing:false};
        this.active.add(entry);
        if (config.type === 'video') {
            media.pause(); media.currentTime = 0;
            this.setMuted(media, !(config.audio && this.audioActive));
            media.pieceMemeOwner = entry;
            this.debug(key, 'attach');
            let previousElapsed = null, previousWall = null;
            const sync = () => {
                if (entry.closed) return;
                const elapsed = Math.max(0,Number(clock.currentTime)||0)/1000;
                const wall = performance.now();
                const clockJump = previousElapsed !== null && Math.abs(
                    elapsed - previousElapsed - (wall - previousWall)/1000*clock.playbackRate) > .08;
                previousElapsed = elapsed; previousWall = wall;
                const length = media.duration;
                const target = Number.isFinite(length) && length > 0
                    ? (config.loop ? elapsed%length : Math.min(elapsed,length)) : elapsed;
                const running = clock.playState === 'running' && (config.loop || elapsed < length);
                if (!running) media.pause();
                // Audible media owns its normal playback position. Repeated small
                // drift corrections flush Firefox's decoder/audio buffer and can
                // prevent audible playback. Still honor explicit clock seeks and
                // paused scrubbing; preserve the existing muted-video sync path.
                const correctPosition = !config.audio || !running || clockJump;
                if (correctPosition && Math.abs(media.currentTime-target) > (running ? .12 : .015) && !media.seeking) {
                    this.debug(key,'sync-seek',{target,clockJump});
                    media.currentTime = target;
                }
                if (running && media.paused && !entry.playing) {
                    entry.playing = true;
                    this.debug(key,'play-request');
                    media.play().then(()=>this.debug(key,'play-resolved')).catch(error=>{
                        this.debug(key,'play-rejected',{error:error.name,message:error.message});
                        if (!entry.closed && error.name !== 'AbortError') console.warn('Piece meme playback:',error);
                    }).finally(()=>{entry.playing=false;if(entry.closed && media.pieceMemeOwner === entry)media.pause();});
                }
                entry.frame = requestAnimationFrame(sync);
            };
            sync();
        }
        entry.finished = clock.finished.catch(error=>{
            if(error.name !== 'AbortError') throw error;
        }).finally(()=>this.close(entry));
    },
    close(entry) {
        if (entry.closed) return;
        this.debug(entry.key,'close');
        entry.closed=true;
        if(entry.frame !== null) cancelAnimationFrame(entry.frame);
        entry.clock.cancel();
        if(entry.media.tagName === 'VIDEO') {this.setMuted(entry.media, true);entry.media.pause();entry.media.currentTime=0;}
        entry.layer.remove();entry.media.remove();entry.host.classList.remove('piece-meme-host');
        this.active.delete(entry);
    },
    removeActor(actor) {for(const entry of [...this.active])if(entry.actor===actor)this.close(entry);},
    reset() {this.audioActive=false;for(const entry of [...this.active])this.close(entry);},
    async finishAll() {
        // Held faces survive timed tails, but never extend the sequence themselves.
        while ([...this.active].some(entry=>!entry.hold))
            await Promise.all([...this.active].filter(entry=>!entry.hold).map(entry=>entry.finished));
    }
};
if (pieceMemeConfig.enabled) {
    // Preload detached nodes before recording; no duplicate hidden media in DOM.
    window.preparePieceMemes = () => pieceMemeSystem.prepare();
    pieceMemeSystem.prepare();
}
