# Ground Symbol (Signal Ground) Specification

## Description
A vertical center line at top connecting to a hollow inverted triangle below, with "GND" text beneath.

## Structure
```
    |
    |
    ^
   / \
  /   \
 /     \
--------
   GND
```

## Drawing Instructions (ReportLab)

### Parameters
- Origin: (x, y) - top of vertical line
- Height of symbol: ~15 points
- Color: Dark Red (#8B0000)

### Steps
1. **Vertical line**: From (x, y) down to triangle top (~8 points)
2. **Inverted triangle**: 3 lines forming hollow inverted triangle
   - Left side: from triangle top to bottom-left
   - Right side: from triangle top to bottom-right
   - Bottom: connecting bottom-left to bottom-right
3. **GND text**: Centered below triangle

### Orientation (based on side)
- **L (left)**: Symbol points right, wire comes from left
- **R (right)**: Symbol points left, wire comes from right
- **B (bottom)**: Symbol points up, wire comes from below
- **T (top)**: Symbol points down, wire comes from above

## SVG Reference
```svg
<svg width="20" height="25" viewBox="0 0 20 25">
  <line x1="10" y1="0" x2="10" y2="8" stroke="#8B0000" stroke-width="1.5"/>
  <polygon points="10,8 3,18 17,18" fill="none" stroke="#8B0000" stroke-width="1.5"/>
  <text x="10" y="24" text-anchor="middle" font-size="5" fill="#8B0000">GND</text>
</svg>
```
