"""Forma base das palavras (went -> go, children -> child) com o simplemma, 100% offline."""


def lemma_of(word: str) -> str:
    w = word.replace("’", "'").lower().strip()
    if "'" in w:          # contrações (don't, I'm) não devem ser lematizadas
        return w
    try:
        from simplemma import lemmatize
        return lemmatize(w, lang="en") or w
    except Exception:
        return w
