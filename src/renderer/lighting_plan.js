// Pure, explicit selection. Stage 6 may choose these recipes from metadata later.
// In Stage 5 !!, check and color do not silently select a treatment or extend time.
function resolveLighting(move) {
    const name = move.effect_preset ?? lightingConfig.defaultPreset;
    const palette = move.effect_palette ?? lightingConfig.defaultPalette;
    if (name !== 'NONE' && !lightingConfig.presets[name]) throw Error('Unknown effect preset: ' + name);
    if (!lightingConfig.palettes[palette]) throw Error('Unknown effect palette: ' + palette);
    if (!lightingConfig.enabled || name === 'NONE') return null;
    return {name, palette, recipe: lightingConfig.presets[name],
        seed: String(move.effect_seed ?? lightingConfig.seed) + ':' +
            [move.from, move.to, move.piece_kind, move.piece_color].join(':')};
}

function effectRandom(seed) {
    // FNV-1a seed + Mulberry32. No wall time, global RNG or replay counters.
    let state = 2166136261;
    for (const char of String(seed)) state = Math.imul(state ^ char.charCodeAt(0), 16777619);
    return () => {
        let value = state += 0x6D2B79F5;
        value = Math.imul(value ^ value >>> 15, value | 1);
        value ^= value + Math.imul(value ^ value >>> 7, value | 61);
        return ((value ^ value >>> 14) >>> 0) / 4294967296;
    };
}

// A finite sampled envelope: pulses continue across the authored hold, fade out
// cleanly, and never use infinite animations or change the timing plan.
function lightPulseFrames(duration, peak, breathing=0, scale=false) {
    if (!(duration>0)) return [{offset:0,opacity:0},{offset:1,opacity:0}];
    const count = Math.max(2, Math.ceil(duration / lightingConfig.sampleInterval));
    const fade = Math.min(lightingConfig.fadeDuration, duration / 2);
    return Array.from({length:count+1}, (_,i) => {
        const t = Math.min(duration, i * lightingConfig.sampleInterval);
        const envelope = Math.min(1, t/fade, (duration-t)/fade);
        const pulse = (1-Math.cos(t/lightingConfig.pulsePeriod*2*Math.PI))/2;
        const frame = {offset:t/duration, opacity:Math.max(0,envelope)*peak*(1-breathing*pulse)};
        if (scale) frame.transform = 'scale(' + (1 + breathing*.15*pulse) + ')';
        return frame;
    });
}
