"""Build the bigram model from the training books and report a sanity check.

    python -m scripts.build_language_model
"""

import numpy as np

from ciphers.alphabet import LETTERS
from ml.language_model import MODEL_PATH, LanguageModel


def main():
    model = LanguageModel.from_corpus()
    model.save()
    info = model.summary()
    print(f"saved {MODEL_PATH}")
    print(f"  books           : {', '.join(info['sources'])}")
    print(f"  bigrams counted : {info['bigrams_counted']:,}")
    print(f"  pairs seen      : {info['distinct_pairs_seen']} / 729")
    print(f"  space share     : {info['space_fraction']:.1%}")

    english = "IT IS A TRUTH UNIVERSALLY ACKNOWLEDGED THAT A SINGLE MAN IN POSSESSION"
    rng = np.random.default_rng(0)
    noise = "".join(rng.choice(list(LETTERS + " "), size=len(english)))
    print("\nsanity check (log-prob per character, higher is more English):")
    print(f"  real English : {model.score_per_char(english):+.3f}")
    print(f"  random noise : {model.score_per_char(noise):+.3f}")

    top = np.dstack(np.unravel_index(np.argsort(model.counts, axis=None)[::-1][:8],
                                     model.counts.shape))[0]
    symbols = LETTERS + "_"
    pairs = ", ".join(f"{symbols[a]}{symbols[b]}" for a, b in top)
    print(f"\n  most common pairs: {pairs}")


if __name__ == "__main__":
    main()
