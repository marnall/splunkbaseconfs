# Service Reliability Scoring Standard

## Score Range
0–100 (higher is better)

## What the Score Represents
A normalized indicator of service reliability based on
log-derived failure behavior.

## Factors That Affect the Score
- Failure frequency
- Sustained degradation
- Repeated instability

## Factors That Do NOT Affect the Score
- Log volume
- INFO noise
- Single isolated spikes

## Interpretation
90–100  Excellent stability  
70–89   Acceptable reliability  
50–69   Degrading / investigate  
<50     Unreliable / action required  

## Known Limitations
- Log-based only
- No infrastructure awareness
- No causal inference
