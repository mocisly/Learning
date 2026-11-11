% Letter pitch labels, calculated from the actual pitch (including accidentals).
#(define (letter-note-name pitch context)
   (let* ((name (list-ref '("C" "D" "E" "F" "G" "A" "B")
                          (ly:pitch-notename pitch)))
          (alter (ly:pitch-alteration pitch))
          (suffix (cond ((= alter 1) "♯♯")
                        ((= alter 1/2) "♯")
                        ((= alter -1/2) "♭")
                        ((= alter -1) "♭♭")
                        (else ""))))
     (string-append name suffix " ")))

namesOnly =
#(define-music-function (music) (ly:music?)
   (music-map
     (lambda (m)
       (if (eq? (ly:music-property m 'name) 'ContextChange)
           (make-music 'SequentialMusic 'elements '())
           m))
     music))
