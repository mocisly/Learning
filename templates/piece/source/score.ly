\version "2.26.0"
% Placeholder only. Replace this with the real score before enabling the piece.
\header { title = "待录入曲谱" tagline = ##f }
\score {
  \new PianoStaff <<
    \new Staff = "up" { \clef treble \time 3/4 R2.*4 }
    \new Staff = "down" { \clef bass \time 3/4 R2.*4 }
  >>
  \layout { }
}
