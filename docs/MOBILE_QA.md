# Responsive table verification — October 30, 2026

The table uses content-sized seat containers, wrapping text, and normal document flow. Opponents sit above the board; the human seat sits below. Desktop uses up to three opponent columns; small screens use wrapping columns and can collapse to one column for enlarged text. No player box has a fixed height or absolute coordinates.

Other layout changes:

- Names, difficulty labels, blind markers, bets, last actions, amounts, and pot summaries can wrap without leaving their containers.
- ASCII cards wrap as complete cards; their internal lines retain monospace spacing.
- Header buttons and betting controls wrap and have touch-sized targets.
- Settings and logs are scrollable inside the viewport, including short landscape screens.
- Results become labeled cards on narrow screens instead of forcing a wide table.
- Input text is at least 1rem to avoid the usual iOS focus zoom at default text size.
- Safe-area padding accommodates display cutouts; reduced-motion preferences are respected.
- Seat IDs are retained when the human is moved below the board, so the right latest action remains attached to each player.

## Browser checks

Checked with synthetic data on an isolated localhost origin. No real match was created, exported, reset, or deleted during these checks. Private histories and game numbering on the public site were not changed.

Viewport sizes: 320×640, 375×667, 390×844, 414×896, 768×1024, 1024×768, 1440×900, and 568×320 landscape.

Scenarios included:

- Every supported seat count, two through six.
- Six seats with long unbroken names, Intermediate difficulty, dealer/blind markers, all-in/out labels, seven-digit stacks, and long action messages.
- Multiple pot summaries and a five-card board including tens and suit symbols.
- 320px width with root text size enlarged to 200%.
- Setup with five bot selectors; settings with long labels; final results with large positive and negative amounts.
- Saved-game list, expanded game controls, and expanded private hand history.

Measured no page-level horizontal overflow, no pairwise seat collisions, and no overflowing seat labels/cards in the tested cases. The settings, results, and archive dialogs stayed inside their containers. The enlarged-text setup heading initially overflowed and was corrected before publication.

These are browser-emulated viewport/text-size checks, not tests on physical iOS/Android devices. Future UI changes should repeat the narrow-width and enlarged-text cases. Do not hide page overflow to mask a layout failure, truncate necessary amounts, or reintroduce fixed seat heights.
