// Pure automatic recipe selection. Logical moves remain immutable; every renderer
// receives the same directed copy. The context belongs to one sequence playback.
function directMove(source, context = {shot:'J',focus:null}) {
    if (!directingConfig.enabled) return {move:source, tier:null, nextContext:context};
    const move = {...source};
    const at = square => ({x:square.charCodeAt(0)-97,y:Number(square[1])-1});
    const from=at(move.from),to=at(move.to);
    const distance=Math.hypot(to.x-from.x,to.y-from.y);
    const annotation=move.annotation;
    const tier=move.director_tier ?? (annotation==='!!'||move.promotion||move.checkmate ? 'HERO'
        : move.capture||move.check||annotation ? 'TACTICAL' : 'NORMAL');
    const settings=directingConfig.tiers[tier];
    if(!settings)throw Error('Unknown director tier: '+tier);
    const strong=tier==='HERO'||(tier==='TACTICAL' &&
        (annotation==='!' || (move.capture && (move.check || distance>=directingConfig.longMove))));
    // Explicit choreography, including inline ~aliases, always wins. An explicit
    // legacy movement preset also prevents automatic choreography substitution.
    if(choreographyConfig.profile==='REFERENCE' && !move.choreography_preset && !move.animation_preset) {
        move.choreography_preset=(strong?directingConfig.strong:directingConfig.ordinary)[move.piece_kind]||'LIFT_MOVE';
    }
    if(choreographyConfig.profile==='REFERENCE' && move.rook_from && !move.rook_choreography_preset)move.rook_choreography_preset='LIFT_MOVE';
    if(reactionConfig.profile==='REFERENCE') {
        if(move.capture_reaction==null)move.capture_reaction=move.en_passant||tier==='NORMAL'?'CAPTURE_SHRINK'
            :tier==='HERO'?'CAPTURE_KNOCKBACK':'CAPTURE_TUMBLE';
        if(move.king_reaction==null)move.king_reaction='KING_RECOIL';
    }
    if(move.effect_preset==null)move.effect_preset=settings.effect;
    if(move.effect_palette==null)move.effect_palette=annotation==='!!'?'CYAN'
        :move.check||annotation==='?'||annotation==='??'?'RED'
        :annotation==='!?'||annotation==='?!'?'ORANGE'
        :annotation==='!'||move.capture||move.promotion?'GREEN':'CYAN';
    // Explicit (Xs), including zero, keeps the existing authored-pause contract.
    if(move.pause_explicit===false || move.pause==null)move.pause=settings.pause;
    if(!move.camera_directive) {
        if(move.rook_from)move.camera_directive='J';
        else if(tier==='HERO')move.camera_directive=distance>=directingConfig.wideHeroMove?'K':'L';
        else if(tier==='TACTICAL')move.camera_directive='K';
        else if(context.shot==='L')move.camera_directive='J';
        else if(context.shot==='K' && context.focus) {
            const focus=at(context.focus);
            if(Math.hypot(to.x-focus.x,to.y-focus.y)>directingConfig.keepMediumRadius)move.camera_directive='J';
        }
    }
    const shot=move.camera_directive||context.shot;
    const nextContext={shot,focus:move.camera_directive ? (shot==='J'?null:move.to) : context.focus};
    return {move,tier,nextContext};
}

// Compose existing systems into one immutable move plan.
function buildMovePlan(source, context) {
    const directed=directMove(source,context);
    const move=directed.move;
    const recipe = resolvePieceMotion(move);
    const forcedNormal = directingConfig.enabled && move.director_tier === 'NORMAL';
    const brilliant = move.annotation === "!!" && !forcedNormal;
    const veryAggressive = directingConfig.enabled && directed.tier === 'HERO' &&
        move.brilliant_mode === 'very_aggressive';
    const aggressive = veryAggressive ? directingConfig.veryAggressive : directingConfig.enabled && directed.tier === 'HERO' &&
        (move.brilliant_mode === 'aggressive' ||
         (brilliant && (move.brilliant_mode ?? directingConfig.brilliantMode) === 'aggressive'))
        ? directingConfig.aggressive : null;
    const directive = cameraConfig.enabled ? move.camera_directive : null;
    const reference = timingConfig.profile === "REFERENCE";
    const cameraDuration = !directive ? 0 : directive === "J"
        ? cameraConfig.wideDuration : cameraConfig.shots[directive].duration;
    const pieceDelay = timingConfig.serialCamera || !directive
        ? (brilliant ? cameraConfig.brilliantPreHold : 0)
        : brilliant ? timingConfig.cameraLeadHero
        : directive === "L" ? timingConfig.cameraLeadClose : timingConfig.cameraLeadNormal;
    // Each recipe supplies its own arrival marker; legacy keyframes are unchanged.
    return Object.freeze({
        move, tier:directed.tier,
        nextContext: veryAggressive && aggressive.spinReturnWide && cameraConfig.transient?.enabled
            ? {shot:'J',focus:null} : directed.nextContext,
        profile: timingConfig.profile, serialCamera: timingConfig.serialCamera,
        cameraDuration, pieceDelay, moveDuration: Math.max(0, recipe.duration),
        choreography: recipe.name,
        reactions: resolveReactions(move),
        lighting: resolveLighting(move, aggressive),
        aggressive,
        contactDelay: Math.max(0, recipe.duration) * recipe.contactOffset,
        holdDuration: Math.max(0, Number(move.pause) || 0) * 1000 +
            (brilliant ? cameraConfig.brilliantPostHold : 0),
        hero: Boolean(reference && cameraConfig.enabled && (directingConfig.enabled ? directed.tier==='HERO' : brilliant)),
        impactStrength: forcedNormal ? 0 : directingConfig.enabled ? (directive==='L' ? 1 : directingConfig.tiers[directed.tier].impact) : null,
        impulse: Boolean(!forcedNormal && reference && cameraConfig.enabled && (directive==='L'||
            (directingConfig.enabled && directingConfig.tiers[directed.tier].impact>0)))
    });
}
