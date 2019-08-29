import itertools
import random

from cytoolz import itertoolz

from .. import utils
from . import utils as aug_utils


def substitute_word_synonyms(aug_toks, *, num=1, pos=None):
    """
    Randomly substitute words for which synonyms are available
    with a randomly selected synonym,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through synonym substitution.
        num (int or float): If int, maximum number of words with available synonyms
            to substitute with a randomly selected synonym; if float, probability
            that a given word with synonyms will be substituted.
        pos (str or Set[str]): Part of speech tag(s) of words to be considered
            for augmentation. If None, all words with synonyms are considered.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    pos = utils.to_collection(pos, str, set)
    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.syns and (pos is None or aug_tok.pos in pos)
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    new_aug_toks = []
    for idx, aug_tok in enumerate(aug_toks):
        if idx in rand_idxs:
            new_aug_toks.append(
                aug_utils.AugTok(
                    text=random.choice(aug_tok.syns),
                    ws=aug_tok.ws,
                    pos=aug_tok.pos,
                    is_word=aug_tok.is_word,
                    syns=aug_tok.syns,  # TODO: re-fetch syns? use []?
                )
            )
        else:
            new_aug_toks.append(aug_tok)
    return new_aug_toks


def insert_word_synonyms(aug_toks, *, num=1, pos=None):
    """
    Randomly insert random synonyms of tokens for which synonyms are available,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through synonym insertion.
        num (int or float): If int, maximum number of words with available synonyms
            from which a random synonym is selected and randomly inserted; if float,
            probability that a given word with synonyms will provide a synonym
            to be inserted.
        pos (str or Set[str]): Part of speech tag(s) of words to be considered
            for augmentation. If None, all words with synonyms are considered.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    pos = utils.to_collection(pos, str, set)
    # bail out on very short sentences to avoid clobbering meaning
    if len(aug_toks) < 3:
        return aug_toks[:]

    cand_aug_toks = [
        aug_tok for aug_tok in aug_toks
        if aug_tok.syns and (pos is None or aug_tok.pos in pos)
    ]
    rand_aug_toks = _select_random_candidates(cand_aug_toks, num)
    rand_idxs = random.sample(range(len(aug_toks)), len(rand_aug_toks))
    if not rand_idxs:
        return aug_toks[:]

    rand_aug_toks = iter(rand_aug_toks)
    new_aug_toks = []
    for idx, (prev_tok, curr_tok) in enumerate(itertoolz.sliding_window(2, [None] + aug_toks)):
        if idx in rand_idxs:
            rand_aug_tok = next(rand_aug_toks)
            if prev_tok:
                # use previous token's whitespace for inserted synonym
                new_tok_ws = prev_tok.ws
                if prev_tok.is_word and not prev_tok.ws:
                    # previous token should have whitespace, if a word
                    new_aug_toks[-1] = aug_utils.AugTok(
                        text=prev_tok.text,
                        ws=" ",
                        pos=prev_tok.pos,
                        is_word=True,
                        syns=prev_tok.syns,
                    )
            else:
                new_tok_ws = " "
            new_aug_toks.append(
                aug_utils.AugTok(
                    text=random.choice(rand_aug_tok.syns),
                    ws=new_tok_ws,
                    pos=rand_aug_tok.pos,
                    is_word=rand_aug_tok.is_word,
                    syns=rand_aug_tok.syns, # TODO: re-fetch syns? use []?
                )
            )
        new_aug_toks.append(curr_tok)
    return new_aug_toks


def swap_words(aug_toks, *, num=1, pos=None):
    """
    Randomly swap the positions of two *adjacent* words,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:class:`AugTok`]): Sequence of tokens to augment
            through position swapping.
        num (int or float): If int, maximum number of adjacent word pairs to swap;
            if float, probability that a given word pair will be swapped.
        pos (str or Set[str]): Part of speech tag(s) of words to be considered
            for augmentation. If None, all words are considered.

    Returns:
        List[:class:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    pos = utils.to_collection(pos, str, set)
    # if we don't require _adjacent_ words, this does the trick
    # if not pos:
    #     pos = set(aug_tok.pos for aug_tok in aug_toks if aug_tok.is_word)
    # cand_idx_pairs = list(
    #     itertools.chain.from_iterable(
    #         itertools.combinations(
    #             (idx for idx, aug_tok in enumerate(aug_toks) if aug_tok.pos == pos_),
    #             2,
    #         )
    #         for pos_ in pos
    #     )
    # )
    cand_idxs = (
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and (pos is None or aug_tok.pos in pos)
    )
    cand_idx_pairs = [
        (idx1, idx2) for idx1, idx2 in itertoolz.sliding_window(2, cand_idxs)
        if idx2 - idx1 == 1
    ]
    rand_idx_pairs = _select_random_candidates(cand_idx_pairs, num)
    if not rand_idx_pairs:
        return aug_toks[:]

    new_aug_toks = aug_toks[:]
    for idx1, idx2 in rand_idx_pairs:
        tok1 = new_aug_toks[idx1]
        tok2 = new_aug_toks[idx2]
        new_aug_toks[idx1] = aug_utils.AugTok(
            text=tok2.text,
            ws=tok1.ws,
            pos=tok2.pos,
            is_word=tok2.is_word,
            syns=tok2.syns,
        )
        new_aug_toks[idx2] = aug_utils.AugTok(
            text=tok1.text,
            ws=tok2.ws,
            pos=tok1.pos,
            is_word=tok1.is_word,
            syns=tok1.syns,
        )
    return new_aug_toks


def delete_words(aug_toks, *, num=1, pos=None):
    """
    Randomly delete words,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:class:`AugTok`]): Sequence of tokens to augment
            through word deletion.
        num (int or float): If int, maximum number of words to delete;
            if float, probability that a given word will be deleted.
        pos (str or Set[str]): Part of speech tag(s) of words to be considered
            for augmentation. If None, all words are considered.

    Returns:
        List[:class:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    pos = utils.to_collection(pos, str, set)
    # bail out on very short sentences to avoid clobbering meaning
    if len(aug_toks) < 3:
        return aug_toks[:]

    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and (pos is None or aug_tok.pos in pos)
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    new_aug_toks = []
    padded_triplets = itertoolz.sliding_window(3, [None] + aug_toks + [None])
    for idx, (prev_tok, curr_tok, next_tok) in enumerate(padded_triplets):
        if idx in rand_idxs:
            # special case: word then [deleted word] then punctuation
            # give deleted word's whitespace to previous word
            if prev_tok and next_tok and prev_tok.is_word and not next_tok.is_word:
                new_aug_toks[-1] = aug_utils.AugTok(
                    text=prev_tok.text,
                    ws=curr_tok.ws,
                    pos=prev_tok.pos,
                    is_word=prev_tok.is_word,
                    syns=prev_tok.syns,
                )
        else:
            new_aug_toks.append(curr_tok)
    return new_aug_toks


def substitute_chars(aug_toks, *, num=1, char_weights=None):
    """
    Randomly substitute a single character in randomly-selected words with another,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through character substitution.
        num (int or float): If int, maximum number of words to modify
            with a random character substitution; if float, probability
            that a given word will be modified.
        char_weights (List[Tuple[str, int]]): Collection of (character, weight) pairs,
            used to perform weighted random selection of characters to substitute
            into selected words. Characters with higher weight are
            more likely to be substituted.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    if not char_weights:
        char_weights = aug_utils.get_char_weights("xx")
    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and len(aug_tok.text) >= 3
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    rand_chars = iter(
        random.choices(
            [char for char, _ in char_weights],
            weights=[weight for _, weight in char_weights],
            k=len(rand_idxs),
        )
    )
    new_aug_toks = []
    for idx, aug_tok in enumerate(aug_toks):
        if idx in rand_idxs:
            text_list = list(aug_tok.text)
            rand_char_idx = random.choice(range(len(text_list)))
            text_list[rand_char_idx] = next(rand_chars)
            new_aug_toks.append(
                aug_utils.AugTok(
                    text="".join(text_list),
                    ws=aug_tok.ws,
                    pos=aug_tok.pos,
                    is_word=aug_tok.is_word,
                    syns=aug_tok.syns,
                )
            )
        else:
            new_aug_toks.append(aug_tok)
    return new_aug_toks


def insert_chars(aug_toks, *, num=1, char_weights=None):
    """
    Randomly insert a character into randomly-selected words,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through character insertion.
        num (int or float): If int, maximum number of words to modify
            with a random character insertion; if float, probability
            that a given word will be modified.
        char_weights (List[Tuple[str, int]]): Collection of (character, weight) pairs,
            used to perform weighted random selection of characters to substitute
            into selected words. Characters with higher weight are
            more likely to be substituted.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    if not char_weights:
        char_weights = aug_utils.get_char_weights("xx")
    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and len(aug_tok.text) >= 3
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    rand_chars = iter(
        random.choices(
            [char for char, _ in char_weights],
            weights=[weight for _, weight in char_weights],
            k=len(rand_idxs),
        )
    )
    new_aug_toks = []
    for idx, aug_tok in enumerate(aug_toks):
        if idx in rand_idxs:
            text_list = list(aug_tok.text)
            rand_char_idx = random.choice(range(len(text_list)))
            text_list.insert(rand_char_idx, next(rand_chars))
            new_aug_toks.append(
                aug_utils.AugTok(
                    text="".join(text_list),
                    ws=aug_tok.ws,
                    pos=aug_tok.pos,
                    is_word=aug_tok.is_word,
                    syns=aug_tok.syns,
                )
            )
        else:
            new_aug_toks.append(aug_tok)
    return new_aug_toks


def swap_chars(aug_toks, *, num=1):
    """
    Randomly swap two *adjacent* characters in randomly-selected words,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through character swapping.
        num (int or float): If int, maximum number of words to modify
            with a random character swap; if float, probability
            that a given word will be modified.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and len(aug_tok.text) >= 3
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    new_aug_toks = []
    for idx, aug_tok in enumerate(aug_toks):
        if idx in rand_idxs:
            text_list = list(aug_tok.text)
            idx = random.choice(range(1, len(text_list)))
            text_list[idx - 1], text_list[idx] = text_list[idx], text_list[idx - 1]
            new_aug_toks.append(
                aug_utils.AugTok(
                    text="".join(text_list),
                    ws=aug_tok.ws,
                    pos=aug_tok.pos,
                    is_word=aug_tok.is_word,
                    syns=aug_tok.syns,
                )
            )
        else:
            new_aug_toks.append(aug_tok)
    return new_aug_toks


def delete_chars(aug_toks, *, num=1):
    """
    Randomly delete a character in randomly-selected words,
    up to ``num`` times or with a probability of ``num``.

    Args:
        aug_toks (List[:obj:`AugTok`]): Sequence of tokens to augment
            through character deletion.
        num (int or float): If int, maximum number of words to modify
            with a random character deletion; if float, probability
            that a given word will be modified.

    Returns:
        List[:obj:`AugTok`]: New, augmented sequence of tokens.
    """
    _validate_aug_toks(aug_toks)
    cand_idxs = [
        idx for idx, aug_tok in enumerate(aug_toks)
        if aug_tok.is_word and len(aug_tok.text) >= 3
    ]
    rand_idxs = set(_select_random_candidates(cand_idxs, num))
    if not rand_idxs:
        return aug_toks[:]

    new_aug_toks = []
    for idx, aug_tok in enumerate(aug_toks):
        if idx in rand_idxs:
            rand_char_idx = random.choice(range(len(aug_tok.text)))
            text = "".join(
                char for char_idx, char in enumerate(aug_tok.text)
                if char_idx != rand_char_idx
            )
            new_aug_toks.append(
                aug_utils.AugTok(
                    text=text,
                    ws=aug_tok.ws,
                    pos=aug_tok.pos,
                    is_word=aug_tok.is_word,
                    syns=aug_tok.syns,
                )
            )
        else:
            new_aug_toks.append(aug_tok)
    return new_aug_toks


def _validate_aug_toks(aug_toks):
    if not (isinstance(aug_toks, list) and isinstance(aug_toks[0], aug_utils.AugTok)):
        raise TypeError(
            "aug_toks must be of type List[:obj:`AugTok`], not {}[{}]".format(
                type(aug_toks), type(aug_toks[0]))
        )


def _select_random_candidates(cands, num):
    """
    Args:
        cands (List[obj])
        num (int or float)

    Returns:
        List[obj]
    """
    if isinstance(num, int) and num >= 0:
        rand_cands = random.sample(cands, min(num, len(cands)))
    elif isinstance(num, float) and 0.0 <= num <= 1.0:
        rand_cands = [cand for cand in cands if random.random() < num]
    else:
        raise ValueError(
            "num={} is invalid; must be an int >= 0 or a float in [0.0, 1.0]".format(num)
        )
    return rand_cands
