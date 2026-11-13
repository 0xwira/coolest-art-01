# She Knits the Sky

Entry for make.fun coolest-art-01 ("Make the coolest art").

A flat 2D ukiyo-e woodblock-style print on visible canvas grain: a
colossal golden koi with crochet-lace fins swims across a deep indigo
night sky, and the braided strand of yarn unraveling from it spirals
down to a rooftop where a tiny grandmother sits knitting the great fish
into the sky. Below, a miniature village glows with lantern-lit windows
between doily-white crochet clouds and a dark patterned sea.

## How it runs

`main.py` (Python 3, standard library only) parses and validates the
bundled `artwork.jpg` (1024x1024): it walks the JPEG marker stream,
checks the competition image gate (at most 1 MiB, at most 1024x1024,
square), estimates the scan's detail density so a soft low-detail
export cannot ship in place of the textured print, then writes the art
to `/output/entry.png` (or `$MAKEFUN_OUTPUT_DIR`) and verifies the
written file byte-for-byte.
