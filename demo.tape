# Demo recording for eqt's README.
#
# Run this on the real machine with EasyEffects actually installed --
# eqt is a front-end for it, so the demo should show a real live gain
# change, not a mock. Safe to run: it only touches eqt's own "_eqt_live"
# working preset, never overwrites a named saved preset.
#
# Install: sudo pacman -S vhs   (or see https://github.com/charmbracelet/vhs)
# Run:     vhs demo.tape
# Output:  demo.gif in this directory -- drop it at the top of README.md
#          right under the title, before "## Features".

Output demo.gif

Set Shell bash
Set FontSize 16
Set Width 900
Set Height 560
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 60ms

Type "eqt"
Enter
Sleep 1500ms

# Move across a few bands, pushing gain up and down to show the live bars.
Right
Right
Up
Up
Sleep 300ms
Up
Sleep 300ms
Right
Down
Down
Sleep 300ms
Right
Right
PageUp
Sleep 500ms

# Reset everything back to flat.
Type "R"
Sleep 800ms

# Open the preset list briefly.
Type "l"
Sleep 1500ms
Escape
Sleep 500ms

Type "q"
Sleep 500ms
