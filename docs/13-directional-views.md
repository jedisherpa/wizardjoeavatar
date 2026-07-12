# Build Directional Views

Create eight authored directional definitions:

```text
north / back
northeast / back-right
east / right
southeast / front-right
south / front
southwest / front-left
west / left
northwest / back-left
```

Do not rotate the front sprite as a bitmap.

Create four canonical views manually:

- front
- back
- left
- right

Create diagonal views by procedurally combining:

- narrower body silhouette
- shifted facial placement
- partial beard visibility
- partial robe opening
- near-arm and far-arm ordering
- per-view staff ordering
- hand-authored correction masks

The diagonal views must have their own reviewed golden images.

The staff may appear behind or in front of the body according to the view.

Use explicit per-view z-order.

Do not mirror a view when doing so would place the staff in the wrong hand.
