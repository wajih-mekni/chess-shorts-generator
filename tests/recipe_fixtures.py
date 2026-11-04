"""Fixed regression recipes: production knobs are intentionally user editable."""
AGGRESSIVE = dict(rotation=12, duration=700, oscillations=4, damping=1.5,
                  zoom=.16, shakeTranslation=26, shakeCycles=12, impactStrength=2.5,
                  lightingMultiplier=1.6, lightSizeMultiplier=1.35, particlesMultiplier=2)
THREE_SECOND = dict(spinTurns=2, spinDuration=2360, spinDirection=1, spinZoomDuration=3000,
                    spinZoomIn=2.2, spinZoomHold=2.2, spinZoomRecoil=1,
                    spinPunchAt=1400/3000, spinRecoilAt=1600/3000, spinOverlap=60,
                    spinSampleInterval=8, spinReturnWide=True, spinReturnWideAt=1600/3000)
