// Finite effect sessions owned by the same move scheduler as travel/reactions.
const lightingSystem = {
    sessions:new Set(), tracks:new Set(), layers:{},
    init() {
        if (!lightingConfig.enabled) return;
        for (const space of ['under','over','viewport']) {
            const node = document.createElement('div');
            node.className = 'lighting-layer lighting-'+space;
            node.setAttribute('aria-hidden','true');
            (space==='viewport' ? document.querySelector('.board-area') : board).appendChild(node);
            this.layers[space] = node;
        }
    },
    begin(move,schedule,plan) { return new LightingSession(move,schedule,plan); },
    reset() { for (const session of [...this.sessions]) session.close(); },
    get finished() { return this.finishAll(); },
    async finishAll() { while(this.tracks.size) await Promise.all([...this.tracks]); }
};

class LightingSession {
    constructor(move,schedule,plan) {
        this.move=move;this.schedule=schedule;this.plan=plan;
        this.nodes=new Set();this.animations=new Set();this.closed=false;
        this.captureEmitted=false;this.particleCount=0;
        if (!plan) return;
        lightingSystem.sessions.add(this);
        this.unsubscribe=schedule.onCue(event=>{
            if(this.closed)return;
            if(event.cue==='captureReaction')this.capture();
            if(event.cue==='contact') {
                this.emitList(plan.recipe.contact,move.to);
                this.capture(); // Reaction disabled/instant move fallback, once only.
            }
            if(event.cue==='holdStart')this.hold(schedule.plan.holdDuration);
        });
    }

    point(square) {
        const p=squareToCoords(square);
        return {x:(p.x+.5)*squareSize,y:(p.y+.5)*squareSize};
    }

    node(shape,space,point,size) {
        const node=document.createElement('div');
        node.className='light-primitive light-'+shape;
        const palette=lightingConfig.palettes[this.plan.palette];
        node.style.setProperty('--light-color',palette.color);
        node.style.setProperty('--light-core',palette.core);
        if(point) {
            node.style.left=(point.x-size/2)+'px';node.style.top=(point.y-size/2)+'px';
            node.style.width=size+'px';node.style.height=size+'px';
        }
        lightingSystem.layers[space].appendChild(node);this.nodes.add(node);
        return node;
    }

    animate(node,frames,duration,delay=0,iterations=1) {
        const animation=node.animate(frames,{duration,delay,iterations,easing:'linear',fill:'both'});
        if(document.timeline.currentTime!==null)animation.startTime=document.timeline.currentTime;
        this.animations.add(animation);
        const task=animation.finished.catch(e=>{if(e.name!=='AbortError')throw e;}).finally(()=>{
            animation.cancel();this.animations.delete(animation);
            node.remove();this.nodes.delete(node);lightingSystem.tracks.delete(task);
        });
        lightingSystem.tracks.add(task);this.schedule.track(task);
        return task;
    }

    emitList(names,square,duration) {
        for (const name of names)this.emit(name,square,duration);
    }

    capture() {
        if(this.captureEmitted || !this.move.capture)return;
        this.captureEmitted=true;
        this.emitList(this.plan.recipe.capture,this.move.capture);
    }

    hold(duration) {
        if (!(duration>0))return;
        this.emitList(this.plan.recipe.hold,this.move.to,duration);
    }

    // Reusable primitive entry point for a future director. Never writes actors.
    emit(name,square,duration) {
        if(this.closed || !this.plan)return;
        if(lightingConfig.particles[name])return this.particles(name,square,duration);
        const config=lightingConfig.lights[name];
        if(!config)throw Error('Unknown lighting primitive: '+name);
        const length=duration ?? config.duration;
        if(!(length>0))return;
        if(config.shape==='ring')return this.rings(square,length,config);
        const node=this.node(config.shape,config.space,
            config.space==='viewport'?null:this.point(square),(config.size||0)*squareSize);
        node.dataset.primitive=name;
        const frames=config.shape==='flash' ? [{opacity:0},{offset:config.peak,opacity:config.opacity},{opacity:0}]
            : lightPulseFrames(length,config.opacity,config.pulse,config.shape==='glow');
        this.animate(node,frames,length);
        if(config.vignette) {
            const shade=this.node('vignette','viewport');
            this.animate(shade,lightPulseFrames(length,config.vignette),length);
        }
    }

    rings(square,duration,config) {
        // Follow the placed badge in board space; an unannotated hero uses the piece.
        const point=annotationBadge.style.display==='flex' ? {
            x:parseFloat(annotationBadge.style.left)+annotationBadge.offsetWidth/2,
            y:parseFloat(annotationBadge.style.top)+annotationBadge.offsetHeight/2
        }:this.point(square);
        const node=this.node('ring','over',point,config.size*squareSize);
        node.dataset.primitive='BADGE_RING';node.style.borderWidth=config.border*squareSize+'px';
        this.animate(node,[{transform:'scale(1)',opacity:0},
            {offset:.15,transform:'scale(1.15)',opacity:config.opacity},
            {transform:'scale('+config.endScale+')',opacity:0}],config.period,0,duration/config.period);
    }

    particles(name,square,duration) {
        const direction=reactionDirection(this.move.from,this.move.to);
        const descriptors=particleDescriptors(name,this.plan.seed,duration,direction,
            Math.max(0,lightingConfig.maxParticles-this.particleCount));
        const point=this.point(square);
        for(const descriptor of descriptors) {
            const node=this.node('particle','over',point,descriptor.size);
            node.classList.add(name==='AMBIENT_DUST'?'light-dust':name==='ARRIVAL_SPARKS'?'light-spark':'light-fragment');
            node.dataset.primitive=name;
            this.animate(node,descriptor.frames,descriptor.duration,descriptor.delay,descriptor.iterations);
        }
        this.particleCount+=descriptors.length;
    }

    close() {
        this.closed=true;this.unsubscribe?.();
        for(const animation of this.animations)animation.cancel();
        for(const node of this.nodes)node.remove();
        this.nodes.clear();lightingSystem.sessions.delete(this);
    }
}
lightingSystem.init();
