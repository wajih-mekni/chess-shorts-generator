// Pure finite particle choreography. The lighting session owns DOM and cleanup.
function particleDescriptors(name, seed, duration, direction, budget=lightingConfig.maxParticles) {
    const config = lightingConfig.particles[name];
    if (!config) throw Error('Unknown particle primitive: '+name);
    const random = effectRandom(seed + ':' + name);
    const dust = name === 'AMBIENT_DUST';
    const window = dust ? duration : config.lifetime;
    if (!(window > 0)) return [];
    // A small staggered pool repeats for the authored window. Very long holds
    // do not allocate more nodes or run out of ambient activity after a cap.
    const batches = dust ? Math.ceil(Math.min(window,config.lifetime)/config.period) : 1;
    const result = [];
    const range = values => values[0]+random()*(values[1]-values[0]);
    for (let batch=0; batch<batches && result.length<budget; batch++) {
        for (let i=0;i<config.count && result.length<budget;i++) {
            const delay = dust ? batch*config.period + random()*config.period*.6 : 0;
            const life = Math.min(config.lifetime, window-delay);
            if (life <= 0) continue;
            const angle = random()*Math.PI*2, distance=range(config.distance)*squareSize;
            const x = dust ? (random()-.5)*config.extent*squareSize : 0;
            const y = dust ? (random()-.5)*config.extent*squareSize : 0;
            const dx = (Math.cos(angle)*config.spread+direction.x*config.bias)*distance;
            const dy = (Math.sin(angle)*config.spread+direction.y*config.bias)*distance;
            const rotation = (random()-.5)*2*config.rotation;
            const transform = (p) => 'translate('+(x+dx*p)+'px,'+
                (y+dy*p+config.gravity*squareSize*p*p)+'px) rotate('+(rotation*p)+'deg) scale('+(1-.6*p)+')';
            result.push({delay, duration:life, iterations:dust ? (window-delay)/life : 1,
                size:range(config.size)*squareSize,
                frames:[{offset:0,transform:transform(0),opacity:0},
                    {offset:.12,transform:transform(.12),opacity:config.opacity},
                    {offset:.55,transform:transform(.55),opacity:config.opacity*.7},
                    {offset:1,transform:transform(1),opacity:0}]});
        }
    }
    return result;
}
