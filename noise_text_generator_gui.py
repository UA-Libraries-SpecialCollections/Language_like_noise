#!/usr/bin/env python3

# Uses Python 3.10 :  C:\Python310>python.exe "S:\Digital Projects\Dev\language_like_noise_text_gen\noise_text_generator_gui.py"
# Developed by the University of Alabama Libraries Digital Services unit
# Jeremiah Colonna-Romano 2026 jjcolonnaromano@ua.edu

"""
Noise Text Dataset Builder

Creates a set of .txt files that look like structured natural language writing, 
Features include:
sentences and paragraph structures
punctuation and capitalization
procedurally generated parts of speech dictionaries
Zipfian word reuse distribution for parts of speech
Entity term strings model NL frequencies
procedurally generated string "words"

custom filenaming output options
Optionaly generate JSON settings file during export for dataset reproducibility / transparency


"""

from __future__ import annotations

import datetime as _dt
import json
import os
import random
import string
import re
import sys
from bisect import bisect_left
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# ----------------------------- Time reference -----------------------------

dtn = _dt.datetime.now()
date_val = dtn.strftime("%Y%m%d%H%M%S")

# ----------------------------- Text generation -----------------------------

ENGLISH_LETTER_FREQ = {
    # Approximate English letter frequency
    "e": 12.70, "t": 9.06, "a": 8.17, "o": 7.51, "i": 6.97, "n": 6.75,
    "s": 6.33, "h": 6.09, "r": 5.99, "d": 4.25, "l": 4.03, "c": 2.78,
    "u": 2.76, "m": 2.41, "w": 2.36, "f": 2.23, "g": 2.02, "y": 1.97,
    "p": 1.93, "b": 1.49, "v": 0.98, "k": 0.77, "j": 0.15, "x": 0.15,
    "q": 0.10, "z": 0.07,
}

# Consonant/vowel clusters to produce "word-like" strings.
SYLLABLE_ONSETS = [
    "", "b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "y", "z",
    "br", "bl", "cr", "cl", "dr", "fr", "fl", "gr", "gl", "pr", "pl", "tr", "st", "sp", "sk", "sm", "sn", "sw",
    "th", "sh", "ch", "ph", "wh", "wr", "kn", "qu",
]
SYLLABLE_NUCLEI = [
    "a", "e", "i", "o", "u",
    "ae", "ai", "ao", "au",
    "ea", "ee", "ei", "eo", "eu",
    "ia", "ie", "io", "iu",
    "oa", "oe", "oi", "oo", "ou",
    "ua", "ue", "ui", "uo",
    "y",
]
SYLLABLE_CODAS = [
    "", "", "",  # bias toward open syllables
    "b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "x", "z",
    "ck", "ct", "ft", "ld", "lf", "lk", "lm", "ln", "lp", "lt", "mp", "nd", "ng", "nk", "nt", "pt", "rd", "rk", "rm", "rn", "rs", "rt", "sk", "sp", "ss", "st",
    "th", "sh", "ch",
]

# Lightweight "POS-like" suffixes to make categories feel more distinct.
# These are still nonsense strings — just shaped to feel English-ish.
NOUN_SUFFIXES = ["", "", "", "", "s", "s", "es", "tion", "ment", "ness"]
VERB_SUFFIXES = ["", "", "", "", "s", "ed", "ing"]
ADJ_SUFFIXES = ["", "", "", "", "al", "ic", "ous", "ive", "ish", "ary"]
ADV_SUFFIXES = ["", "ly", "ly", "ly", "wise", "ward"]


def clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def weighted_choice(items: List[str], weights: List[float]) -> str:
    return random.choices(items, weights=weights, k=1)[0]


def sample_word_length(mean: float, stdev: float, min_len: int, max_len: int) -> int:
    if stdev <= 0:
        return clamp_int(int(round(mean)), min_len, max_len)

    # Truncated normal sampling (simple rejection); bounded and fast for small ranges.
    for _ in range(60):
        v = random.gauss(mean, stdev)
        n = int(round(v))
        if min_len <= n <= max_len:
            return n
    return clamp_int(int(round(mean)), min_len, max_len)


def generate_word_uniform(length: int, alphabet: str, allow_double: bool = True) -> str:
    if length <= 0:
        return ""
    chars = []
    prev = ""
    for _ in range(length):
        c = random.choice(alphabet)
        if not allow_double and c == prev:
            for __ in range(6):
                c2 = random.choice(alphabet)
                if c2 != prev:
                    c = c2
                    break
        chars.append(c)
        prev = c
    return "".join(chars)


def generate_word_letterfreq(length: int, allow_double: bool = True) -> str:
    letters = list(ENGLISH_LETTER_FREQ.keys())
    weights = list(ENGLISH_LETTER_FREQ.values())
    if length <= 0:
        return ""
    out = []
    prev = ""
    for _ in range(length):
        c = weighted_choice(letters, weights)
        if not allow_double and c == prev:
            for __ in range(6):
                c2 = weighted_choice(letters, weights)
                if c2 != prev:
                    c = c2
                    break
        out.append(c)
        prev = c
    return "".join(out)


def generate_word_syllable(target_len: int, min_syllables: int, max_syllables: int, allow_double: bool = True) -> str:
    syllables = random.randint(min_syllables, max_syllables)
    parts: List[str] = []
    prev = ""
    for _ in range(syllables):
        onset = random.choice(SYLLABLE_ONSETS)
        nucleus = random.choice(SYLLABLE_NUCLEI)
        coda = random.choice(SYLLABLE_CODAS)
        s = onset + nucleus + coda

        if not allow_double and prev and s and prev[-1] == s[0]:
            s = s[1:] if len(s) > 1 else s

        parts.append(s)
        prev = s

    word = "".join(parts) or "a"

    if len(word) > target_len:
        return word[:target_len]

    vowels = "aeiouy"
    consonants = "bcdfghjklmnpqrstvwxz"
    while len(word) < target_len:
        last = word[-1]
        word += random.choice(consonants if last in vowels else vowels)

    return word


def maybe_capitalize(word: str, style: str) -> str:
    # style: "none", "title", "upper"
    if not word:
        return word
    if style == "none":
        return word
    if style == "title":
        return word[0].upper() + word[1:]
    if style == "upper":
        return word.upper()
    return word


class ZipfSampler:
    """
    Zipf-like sampler: item rank r has weight proportional to 1 / r^s.
    Uses a precomputed CDF for fast sampling.
    """
    def __init__(self, items: List[str], exponent: float = 1.07):
        if not items:
            raise ValueError("ZipfSampler requires a non-empty items list.")
        self.items = items
        self.exponent = max(0.01, float(exponent))
        total = 0.0
        cdf: List[float] = []
        for r in range(1, len(items) + 1):
            total += 1.0 / (r ** self.exponent)
            cdf.append(total)
        self._total = total
        self._cdf = cdf

    def sample(self) -> str:
        x = random.random() * self._total
        i = bisect_left(self._cdf, x)
        if i >= len(self.items):
            i = len(self.items) - 1
        return self.items[i]

    def vocab(self) -> List[str]:
        return list(self.items)


# ----------------------------- Configuration ------------------------------

@dataclass
class NoiseTextConfig:
    # dataset
    num_files: int = 25
    sentences_min: int = 8
    sentences_max: int = 16
    words_min: int = 12
    words_max: int = 20

    # word length distribution (English-ish defaults)
    word_len_mean: float = 4.7
    word_len_stdev: float = 1.8
    word_len_min: int = 2
    word_len_max: int = 12

    # generator mode
    generator_mode: str = "syllable"  # "syllable" | "letterfreq" | "uniform"
    uniform_alphabet: str = "abcdefghijklmnopqrstuvwxyz"
    allow_double_letters: bool = True

    # syllable settings
    syllables_min: int = 1
    syllables_max: int = 4

    # Zipf-like reuse + POS/entity shaping
    enable_zipf_reuse: bool = True
    zipf_exponent: float = 1.07
    pos_like_suffixes: bool = True

    function_vocab_size: int = 180      # split into DET/PREP/CONJ/PRON
    content_vocab_size: int = 3000      # split into NOUN/VERB/ADJ/ADV
    entity_vocab_size: int = 250        # entity phrases (Title Case)

    entity_tokens_min: int = 1
    entity_tokens_max: int = 3
    entity_sentence_start_rate: float = 0.08   # chance a sentence starts with an entity
    entity_replace_noun_rate: float = 0.14     # chance a noun slot becomes an entity phrase

    # sentence styling
    capitalize_sentence_start: bool = True
    internal_proper_noun_rate: float = 0.02  # extra Title Case on non-entity words
    all_caps_rate: float = 0.004             # chance a random word is ALL CAPS

    # punctuation / structure
    comma_rate: float = 0.12
    max_commas_per_sentence: int = 2

    period_weight: float = 0.86
    question_weight: float = 0.09
    exclaim_weight: float = 0.05

    paragraph_break_min_sentences: int = 1
    paragraph_break_max_sentences: int = 9
    enable_paragraphs: bool = True

    # output
    filename_prefix: str = "u9999_1234567_"
    filename_suffix: str = "_0001"
    start_index: int = 1
    zero_pad_width: int = 7
    extension: str = ".txt"
    overwrite_existing: bool = False

    seed: str = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(10))  # empty => random

    # JSON settings sidecar
    export_settings_json: bool = True
    settings_filename: str = f"dataset_settings_{seed}_{date_val}.json"
    include_file_list_in_json: bool = True
    include_vocab_in_json: bool = False  # can be large if enabled


# ---------------------------- Generator engine ----------------------------

class NoiseTextGenerator:
    def __init__(self, cfg: NoiseTextConfig):
        self.cfg = cfg
        self.lex: Dict[str, ZipfSampler] = {}
        self._derived_sizes: Dict[str, int] = {}

        if cfg.enable_zipf_reuse:
            self._init_zipf_lexicons()

    # ----- base word creation -----

    def _base_word(self, length: int) -> str:
        cfg = self.cfg
        if cfg.generator_mode == "uniform":
            alphabet = cfg.uniform_alphabet.strip() or "abcdefghijklmnopqrstuvwxyz"
            return generate_word_uniform(length, alphabet=alphabet, allow_double=cfg.allow_double_letters)
        if cfg.generator_mode == "letterfreq":
            return generate_word_letterfreq(length, allow_double=cfg.allow_double_letters)
        return generate_word_syllable(
            target_len=length,
            min_syllables=cfg.syllables_min,
            max_syllables=cfg.syllables_max,
            allow_double=cfg.allow_double_letters,
        )

    def _sample_len_for_pos(self, pos: str) -> int:
        cfg = self.cfg

        # Keep everything within user bounds, but bias different POS slightly.
        min_len = cfg.word_len_min
        max_len = cfg.word_len_max

        if pos in {"DET", "PREP", "CONJ", "PRON"}:
            max_len = min(max_len, 6)
            mean = max(2.0, cfg.word_len_mean - 1.2)
            sd = max(0.6, cfg.word_len_stdev * 0.75)
            return sample_word_length(mean, sd, min_len, max_len)

        if pos == "ADV":
            mean = cfg.word_len_mean + 0.8
            sd = cfg.word_len_stdev
            return sample_word_length(mean, sd, min_len, max_len)

        if pos in {"NOUN", "VERB", "ADJ"}:
            mean = cfg.word_len_mean + 1.0
            sd = cfg.word_len_stdev
            return sample_word_length(mean, sd, min_len, max_len)

        # ENTITY token lengths
        mean = cfg.word_len_mean + 1.4
        sd = cfg.word_len_stdev
        return sample_word_length(mean, sd, min_len, max_len)

    def _apply_suffix(self, base: str, suffix: str, max_len: int) -> str:
        if not suffix:
            return base
        if len(base) + len(suffix) > max_len:
            return base
        return base + suffix

    def _make_pos_token(self, pos: str) -> str:
        cfg = self.cfg
        max_len = cfg.word_len_max

        target = self._sample_len_for_pos(pos)
        suffix = ""

        if cfg.pos_like_suffixes:
            if pos == "NOUN":
                suffix = random.choice(NOUN_SUFFIXES)
            elif pos == "VERB":
                suffix = random.choice(VERB_SUFFIXES)
            elif pos == "ADJ":
                suffix = random.choice(ADJ_SUFFIXES)
            elif pos == "ADV":
                suffix = random.choice(ADV_SUFFIXES)

        # Generate base a bit shorter if suffix exists
        base_target = target - len(suffix)
        if base_target < cfg.word_len_min:
            base_target = cfg.word_len_min

        base = self._base_word(base_target)
        tok = self._apply_suffix(base, suffix, max_len)

        # Ensure printable / no spaces
        tok = "".join(ch for ch in tok if ch.isprintable() and not ch.isspace())
        return tok or "a"

    # ----- zipf lexicon building -----

    def _split_sizes(self) -> Dict[str, int]:
        """
        Convert aggregate vocab sizes into per-POS sizes.
        Keeps a stable split so the UI stays simple.
        """
        cfg = self.cfg

        func = max(10, int(cfg.function_vocab_size))
        cont = max(20, int(cfg.content_vocab_size))

        # Function: DET/PREP/CONJ/PRON
        det = max(12, round(func * 0.22))
        prep = max(18, round(func * 0.36))
        conj = max(8, round(func * 0.14))
        pron = max(10, func - det - prep - conj)

        # Content: NOUN/VERB/ADJ/ADV
        noun = max(100, round(cont * 0.38))
        verb = max(80, round(cont * 0.27))
        adj = max(80, round(cont * 0.27))
        adv = max(30, cont - noun - verb - adj)

        return {
            "DET": int(det),
            "PREP": int(prep),
            "CONJ": int(conj),
            "PRON": int(pron),
            "NOUN": int(noun),
            "VERB": int(verb),
            "ADJ": int(adj),
            "ADV": int(adv),
            "ENTITY": int(max(10, cfg.entity_vocab_size)),
        }

    def _build_vocab(self, pos: str, size: int, title_case: bool = False) -> List[str]:
        vocab: set[str] = set()
        attempts = 0
        max_attempts = max(2000, size * 60)

        while len(vocab) < size and attempts < max_attempts:
            attempts += 1
            tok = self._make_pos_token(pos)
            if title_case:
                tok = maybe_capitalize(tok, "title")
            if tok and " " not in tok and "\n" not in tok and "\t" not in tok:
                vocab.add(tok)

        vocab_list = list(vocab)
        random.shuffle(vocab_list)
        if not vocab_list:
            vocab_list = [maybe_capitalize("a", "title") if title_case else "a"]
        return vocab_list

    def _build_entity_phrases(self, size: int) -> List[str]:
        cfg = self.cfg
        phrases: set[str] = set()
        attempts = 0
        max_attempts = max(2000, size * 80)

        def sample_len() -> int:
            lo, hi = cfg.entity_tokens_min, cfg.entity_tokens_max
            lo = max(1, int(lo))
            hi = max(lo, int(hi))
            if hi == 1:
                return 1
            if lo <= 2 <= hi and random.random() < 0.60:
                return 2
            return random.randint(lo, hi)

        while len(phrases) < size and attempts < max_attempts:
            attempts += 1
            k = sample_len()
            parts = []
            for _ in range(k):
                tok = self._make_pos_token("ENTITY")
                tok = maybe_capitalize(tok, "title")
                parts.append(tok)
            phrase = " ".join(parts)
            if phrase:
                phrases.add(phrase)

        out = list(phrases)
        random.shuffle(out)
        if not out:
            out = ["A"]
        return out

    def _init_zipf_lexicons(self) -> None:
        cfg = self.cfg
        sizes = self._split_sizes()
        self._derived_sizes = dict(sizes)

        self.lex["DET"] = ZipfSampler(self._build_vocab("DET", sizes["DET"]), exponent=cfg.zipf_exponent)
        self.lex["PREP"] = ZipfSampler(self._build_vocab("PREP", sizes["PREP"]), exponent=cfg.zipf_exponent)
        self.lex["CONJ"] = ZipfSampler(self._build_vocab("CONJ", sizes["CONJ"]), exponent=cfg.zipf_exponent)
        self.lex["PRON"] = ZipfSampler(self._build_vocab("PRON", sizes["PRON"]), exponent=cfg.zipf_exponent)
        self.lex["NOUN"] = ZipfSampler(self._build_vocab("NOUN", sizes["NOUN"]), exponent=cfg.zipf_exponent)
        self.lex["VERB"] = ZipfSampler(self._build_vocab("VERB", sizes["VERB"]), exponent=cfg.zipf_exponent)
        self.lex["ADJ"] = ZipfSampler(self._build_vocab("ADJ", sizes["ADJ"]), exponent=cfg.zipf_exponent)
        self.lex["ADV"] = ZipfSampler(self._build_vocab("ADV", sizes["ADV"]), exponent=cfg.zipf_exponent)

        entities = self._build_entity_phrases(sizes["ENTITY"])
        self.lex["ENTITY"] = ZipfSampler(entities, exponent=cfg.zipf_exponent)

    def derived_sizes(self) -> Dict[str, int]:
        return dict(self._derived_sizes)

    # ----- punctuation helpers -----

    def _sentence_end_punct(self) -> str:
        cfg = self.cfg
        items = [".", "?", "!"]
        weights = [max(0.0, cfg.period_weight), max(0.0, cfg.question_weight), max(0.0, cfg.exclaim_weight)]
        if sum(weights) <= 0:
            return "."
        return weighted_choice(items, weights)

    def _maybe_insert_commas(self, words: List[str], protect_after: Optional[List[bool]] = None) -> List[str]:
        cfg = self.cfg
        if len(words) < 6 or cfg.max_commas_per_sentence <= 0:
            return words

        if random.random() > cfg.comma_rate:
            return words

        protect_after = protect_after or [False] * len(words)
        valid = [i for i in range(1, len(words) - 1) if not protect_after[i]]
        if not valid:
            return words

        k = 1 if cfg.max_commas_per_sentence == 1 else random.randint(1, cfg.max_commas_per_sentence)
        k = min(k, len(valid))
        positions = set(random.sample(valid, k=k))

        new_words = []
        for i, w in enumerate(words):
            new_words.append(w + "," if i in positions else w)
        return new_words

    # ----- sentence generation: POS-like Zipf mode -----

    def _next_pos(self, prev: str) -> str:
        T: Dict[str, List[Tuple[str, float]]] = {
            "START": [("DET", 0.40), ("PRON", 0.16), ("NOUN", 0.22), ("ADJ", 0.10), ("ENTITY", 0.12)],
            "DET":   [("ADJ", 0.38), ("NOUN", 0.52), ("ENTITY", 0.10)],
            "PRON":  [("VERB", 0.84), ("ADV", 0.10), ("VERB", 0.06)],
            "ADJ":   [("ADJ", 0.15), ("NOUN", 0.85)],
            "NOUN":  [("VERB", 0.52), ("PREP", 0.18), ("CONJ", 0.12), ("END", 0.18)],
            "ENTITY":[("VERB", 0.55), ("PREP", 0.17), ("CONJ", 0.10), ("END", 0.18)],
            "VERB":  [("DET", 0.30), ("PRON", 0.06), ("NOUN", 0.14), ("ENTITY", 0.10), ("ADV", 0.18), ("PREP", 0.12), ("END", 0.10)],
            "ADV":   [("VERB", 0.34), ("PREP", 0.20), ("END", 0.46)],
            "PREP":  [("DET", 0.58), ("NOUN", 0.32), ("ENTITY", 0.10)],
            "CONJ":  [("DET", 0.34), ("PRON", 0.15), ("NOUN", 0.25), ("ADJ", 0.14), ("ENTITY", 0.12)],
        }

        opts = T.get(prev, T["NOUN"])
        items = [p for p, _ in opts]
        weights = [w for _, w in opts]
        return weighted_choice(items, weights)

    def _zipf_token_for_pos(self, pos: str) -> str:
        if pos in self.lex:
            return self.lex[pos].sample()
        wl = sample_word_length(self.cfg.word_len_mean, self.cfg.word_len_stdev, self.cfg.word_len_min, self.cfg.word_len_max)
        return self._base_word(wl)

    def generate_sentence_zipf(self) -> str:
        cfg = self.cfg
        target_words = random.randint(cfg.words_min, cfg.words_max)

        words: List[str] = []
        protect_after: List[bool] = []

        prev = "START"
        if random.random() < cfg.entity_sentence_start_rate:
            phrase = self._zipf_token_for_pos("ENTITY")
            parts = phrase.split(" ")
            for j, p in enumerate(parts):
                words.append(p)
                protect_after.append(j < len(parts) - 1)
            prev = "ENTITY"

        max_soft = cfg.words_max + 8
        last_pos = prev

        while len(words) < target_words:
            pos = self._next_pos(last_pos)

            if pos == "END":
                if len(words) >= cfg.words_min:
                    break
                pos = "NOUN"

            if pos == "NOUN" and random.random() < cfg.entity_replace_noun_rate:
                pos = "ENTITY"

            if pos == "ENTITY":
                phrase = self._zipf_token_for_pos("ENTITY")
                parts = phrase.split(" ")
                for j, p in enumerate(parts):
                    words.append(p)
                    protect_after.append(j < len(parts) - 1)
                last_pos = "ENTITY"
            else:
                tok = self._zipf_token_for_pos(pos)
                words.append(tok)
                protect_after.append(False)
                last_pos = pos

        endable = {"NOUN", "VERB", "ADV", "ENTITY"}
        while len(words) < max_soft and last_pos not in endable:
            pos = self._next_pos(last_pos)
            if pos == "END":
                break

            if pos == "NOUN" and random.random() < cfg.entity_replace_noun_rate:
                pos = "ENTITY"

            if pos == "ENTITY":
                phrase = self._zipf_token_for_pos("ENTITY")
                parts = phrase.split(" ")
                for j, p in enumerate(parts):
                    words.append(p)
                    protect_after.append(j < len(parts) - 1)
                last_pos = "ENTITY"
            else:
                words.append(self._zipf_token_for_pos(pos))
                protect_after.append(False)
                last_pos = pos

        if len(words) > max_soft:
            words = words[:max_soft]
            protect_after = protect_after[:max_soft]

        def is_entity_token(w: str) -> bool:
            return bool(w) and w[0].isupper()

        for i, w in enumerate(words):
            if is_entity_token(w):
                continue
            if random.random() < cfg.all_caps_rate:
                words[i] = maybe_capitalize(w, "upper")
            elif random.random() < cfg.internal_proper_noun_rate:
                words[i] = maybe_capitalize(w, "title")

        words = self._maybe_insert_commas(words, protect_after=protect_after)

        if cfg.capitalize_sentence_start and words:
            words[0] = maybe_capitalize(words[0], "title")

        punct = self._sentence_end_punct()
        return " ".join(words) + punct

    # ----- sentence generation: original random mode -----

    def generate_sentence_random(self) -> str:
        cfg = self.cfg
        n_words = random.randint(cfg.words_min, cfg.words_max)

        words: List[str] = []
        for _ in range(n_words):
            wl = sample_word_length(cfg.word_len_mean, cfg.word_len_stdev, cfg.word_len_min, cfg.word_len_max)
            w = self._base_word(wl)

            if random.random() < cfg.all_caps_rate:
                w = maybe_capitalize(w, "upper")
            elif random.random() < cfg.internal_proper_noun_rate:
                w = maybe_capitalize(w, "title")

            words.append(w)

        words = self._maybe_insert_commas(words)

        if cfg.capitalize_sentence_start and words:
            words[0] = maybe_capitalize(words[0], "title")

        punct = self._sentence_end_punct()
        return " ".join(words) + punct

    def generate_sentence(self) -> str:
        if self.cfg.enable_zipf_reuse:
            return self.generate_sentence_zipf()
        return self.generate_sentence_random()

    # ----- document generation -----

    def generate_document(self) -> str:
        cfg = self.cfg
        n_sentences = random.randint(cfg.sentences_min, cfg.sentences_max)
        sentences = [self.generate_sentence() for _ in range(n_sentences)]

        if not cfg.enable_paragraphs or n_sentences < 6:
            return " ".join(sentences) + "\n"

        out_lines: List[str] = []
        idx = 0
        while idx < n_sentences:
            block = random.randint(cfg.paragraph_break_min_sentences, cfg.paragraph_break_max_sentences)
            chunk = sentences[idx: idx + block]
            out_lines.append(" ".join(chunk))
            idx += block
        return "\n\n".join(out_lines) + "\n"


# ------------------------------- GUI helpers -------------------------------

class LabeledEntry(ttk.Frame):
    """Label + entry, with helpers to parse values."""
    def __init__(self, master, text: str, width: int = 10):
        super().__init__(master)
        self.label = ttk.Label(self, text=text)
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.entry.grid(row=0, column=1, sticky="w")

    def set(self, value) -> None:
        self.var.set(str(value))

    def get_str(self) -> str:
        return self.var.get()

    def get_int(self, *, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        s = self.get_str().strip()
        if not re.fullmatch(r"[+-]?\d+", s):
            raise ValueError(f"Expected integer for '{self.label.cget('text')}', got: {s!r}")
        v = int(s)
        if min_value is not None and v < min_value:
            raise ValueError(f"'{self.label.cget('text')}' must be ≥ {min_value}")
        if max_value is not None and v > max_value:
            raise ValueError(f"'{self.label.cget('text')}' must be ≤ {max_value}")
        return v

    def get_float(self, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
        s = self.get_str().strip()
        try:
            v = float(s)
        except ValueError:
            raise ValueError(f"Expected number for '{self.label.cget('text')}', got: {s!r}")
        if min_value is not None and v < min_value:
            raise ValueError(f"'{self.label.cget('text')}' must be ≥ {min_value}")
        if max_value is not None and v > max_value:
            raise ValueError(f"'{self.label.cget('text')}' must be ≤ {max_value}")
        return v


class RangeRow(ttk.Frame):
    """A 'min/max' pair with a shared label."""
    def __init__(self, master, text: str, width: int = 8):
        super().__init__(master)
        self.label = ttk.Label(self, text=text)
        self.min_var = tk.StringVar()
        self.max_var = tk.StringVar()
        self.min_entry = ttk.Entry(self, textvariable=self.min_var, width=width)
        self.max_entry = ttk.Entry(self, textvariable=self.max_var, width=width)
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(self, text="min").grid(row=0, column=1, sticky="e", padx=(0, 4))
        self.min_entry.grid(row=0, column=2, sticky="w")
        ttk.Label(self, text="max").grid(row=0, column=3, sticky="e", padx=(10, 4))
        self.max_entry.grid(row=0, column=4, sticky="w")

    def set(self, min_value, max_value) -> None:
        self.min_var.set(str(min_value))
        self.max_var.set(str(max_value))

    def get_int_range(self, *, min_value: int = 0, max_value: Optional[int] = None) -> Tuple[int, int]:
        def parse_int(name: str, s: str) -> int:
            s = s.strip()
            if not re.fullmatch(r"[+-]?\d+", s):
                raise ValueError(f"Expected integer for '{self.label.cget('text')} {name}', got: {s!r}")
            return int(s)

        lo = parse_int("min", self.min_var.get())
        hi = parse_int("max", self.max_var.get())
        if lo < min_value:
            raise ValueError(f"'{self.label.cget('text')} min' must be ≥ {min_value}")
        if max_value is not None and hi > max_value:
            raise ValueError(f"'{self.label.cget('text')} max' must be ≤ {max_value}")
        if lo > hi:
            raise ValueError(f"'{self.label.cget('text')}' min must be ≤ max")
        return lo, hi


# --------------------------------- The app ---------------------------------

class App(ttk.Frame):
    TOOL_VERSION = "1.1"

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master.title("Noise Text Dataset Builder")
        self.master.geometry("1020x760")
        self.master.minsize(940, 680)

        self.cfg = NoiseTextConfig()

        self._build_ui()
        self._load_defaults_into_ui()
        self._update_preview()

    def _build_ui(self) -> None:
        self.grid(row=0, column=0, sticky="nsew")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Left panel becomes scrollable because the number of settings can exceed screen height.
        left_container = ttk.Frame(paned)
        right = ttk.Frame(paned, padding=12)
        paned.add(left_container, weight=1)
        paned.add(right, weight=2)

        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(left_container, highlightthickness=0)
        vbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")

        # Inner frame that holds all settings widgets
        left = ttk.Frame(canvas, padding=12)
        left_window_id = canvas.create_window((0, 0), window=left, anchor="nw")

        def _sync_scrollregion(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(_event=None) -> None:
            # Keep the inner frame width aligned with the visible canvas area
            canvas.itemconfigure(left_window_id, width=canvas.winfo_width())

        left.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)

        def _is_descendant(widget: tk.Misc, ancestor: tk.Misc) -> bool:
            w = widget
            while w is not None:
                if w == ancestor:
                    return True
                w = getattr(w, "master", None)
            return False

        def _wheel(event) -> Optional[str]:
            # Only scroll the settings panel when the cursor is over the left panel
            # (so the preview/log area can scroll independently).
            if not _is_descendant(event.widget, left_container):
                return None

            # Windows/macOS use event.delta; many Linux setups use Button-4/5.
            if getattr(event, "delta", 0):
                if sys.platform.startswith("win"):
                    steps = int(-event.delta / 120)
                else:
                    # macOS trackpads typically report small deltas
                    steps = -1 if event.delta > 0 else 1
                canvas.yview_scroll(steps, "units")
                return "break"

            if getattr(event, "num", None) in (4, 5):
                canvas.yview_scroll(-3 if event.num == 4 else 3, "units")
                return "break"

            return None

        # Bind globally and filter by panel; this keeps scrolling working even when the cursor is
        # over child widgets (entries, buttons, etc.) inside the canvas.
        self.master.bind_all("<MouseWheel>", _wheel)
        self.master.bind_all("<Button-4>", _wheel)
        self.master.bind_all("<Button-5>", _wheel)

        left.grid_columnconfigure(0, weight=1)

        # Dataset group
        g_dataset = ttk.Labelframe(left, text="Dataset size & structure", padding=10)
        g_dataset.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        g_dataset.grid_columnconfigure(0, weight=1)

        self.e_num_files = LabeledEntry(g_dataset, "Number of files", width=10)
        self.r_sentences = RangeRow(g_dataset, "Sentences per file", width=8)
        self.r_words = RangeRow(g_dataset, "Words per sentence", width=8)

        self.e_num_files.grid(row=0, column=0, sticky="w", pady=4)
        self.r_sentences.grid(row=1, column=0, sticky="w", pady=4)
        self.r_words.grid(row=2, column=0, sticky="w", pady=4)

        # Word length group
        g_wordlen = ttk.Labelframe(left, text="Word length distribution", padding=10)
        g_wordlen.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        g_wordlen.grid_columnconfigure(0, weight=1)

        self.e_word_mean = LabeledEntry(g_wordlen, "Average letters per word", width=10)
        self.e_word_sd = LabeledEntry(g_wordlen, "Word length stdev", width=10)
        self.r_wordlen_bounds = RangeRow(g_wordlen, "Word length bounds", width=8)

        self.e_word_mean.grid(row=0, column=0, sticky="w", pady=4)
        self.e_word_sd.grid(row=1, column=0, sticky="w", pady=4)
        self.r_wordlen_bounds.grid(row=2, column=0, sticky="w", pady=4)

        # Generator group
        g_gen = ttk.Labelframe(left, text="Base word generator", padding=10)
        g_gen.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        g_gen.grid_columnconfigure(0, weight=1)

        self.gen_mode = tk.StringVar(value="syllable")
        modes = ttk.Frame(g_gen)
        ttk.Label(modes, text="Mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Radiobutton(
            modes, text="Syllable-based (most word-like)", variable=self.gen_mode, value="syllable",
            command=self._on_mode_change
        ).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(
            modes, text="English letter-frequency", variable=self.gen_mode, value="letterfreq",
            command=self._on_mode_change
        ).grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(
            modes, text="Uniform random letters", variable=self.gen_mode, value="uniform",
            command=self._on_mode_change
        ).grid(row=2, column=1, sticky="w")
        modes.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.cb_allow_double = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_gen, text="Allow doubled letters (e.g., 'tt')", variable=self.cb_allow_double,
            command=self._update_preview
        ).grid(row=1, column=0, sticky="w", pady=4)

        self.r_syllables = RangeRow(g_gen, "Syllables per word", width=8)
        self.r_syllables.grid(row=2, column=0, sticky="w", pady=4)

        self.e_alphabet = LabeledEntry(g_gen, "Alphabet (uniform mode)", width=30)
        self.e_alphabet.grid(row=3, column=0, sticky="w", pady=4)

        # Zipf group
        g_zipf = ttk.Labelframe(left, text="Zipf-like reuse, POS lexicons & entities", padding=10)
        g_zipf.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        g_zipf.grid_columnconfigure(0, weight=1)

        self.cb_zipf = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_zipf, text="Enable Zipf-like word reuse (more natural repetition)",
            variable=self.cb_zipf, command=self._on_zipf_toggle
        ).grid(row=0, column=0, sticky="w", pady=4)

        self.e_zipf_exp = LabeledEntry(g_zipf, "Zipf exponent (≈ 1.0)", width=10)
        self.e_zipf_exp.grid(row=1, column=0, sticky="w", pady=4)

        self.cb_pos_suffix = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_zipf, text="Add POS-like suffixes (e.g., -ly, -ing) in lexicons",
            variable=self.cb_pos_suffix, command=self._update_preview
        ).grid(row=2, column=0, sticky="w", pady=4)

        self.e_func_vocab = LabeledEntry(g_zipf, "Function vocab size (DET/PREP/CONJ/PRON)", width=10)
        self.e_cont_vocab = LabeledEntry(g_zipf, "Content vocab size (NOUN/VERB/ADJ/ADV)", width=10)
        self.e_ent_vocab = LabeledEntry(g_zipf, "Entity phrase vocab size", width=10)
        self.e_func_vocab.grid(row=3, column=0, sticky="w", pady=4)
        self.e_cont_vocab.grid(row=4, column=0, sticky="w", pady=4)
        self.e_ent_vocab.grid(row=5, column=0, sticky="w", pady=4)

        self.r_ent_len = RangeRow(g_zipf, "Entity words per phrase", width=8)
        self.r_ent_len.grid(row=6, column=0, sticky="w", pady=4)

        self.e_ent_start_rate = LabeledEntry(g_zipf, "Entity at sentence start rate (0..1)", width=10)
        self.e_ent_noun_rate = LabeledEntry(g_zipf, "Replace NOUN with entity rate (0..1)", width=10)
        self.e_ent_start_rate.grid(row=7, column=0, sticky="w", pady=4)
        self.e_ent_noun_rate.grid(row=8, column=0, sticky="w", pady=4)

        # Styling group
        g_style = ttk.Labelframe(left, text="Sentence styling", padding=10)
        g_style.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        g_style.grid_columnconfigure(0, weight=1)

        self.cb_cap_start = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_style, text="Capitalize first word of each sentence", variable=self.cb_cap_start,
            command=self._update_preview
        ).grid(row=0, column=0, sticky="w", pady=4)

        self.e_proper_rate = LabeledEntry(g_style, "Extra Title-Case word rate (0..1)", width=10)
        self.e_caps_rate = LabeledEntry(g_style, "ALL-CAPS word rate (0..1)", width=10)
        self.e_proper_rate.grid(row=1, column=0, sticky="w", pady=4)
        self.e_caps_rate.grid(row=2, column=0, sticky="w", pady=4)

        # Punctuation group
        g_punct = ttk.Labelframe(left, text="Punctuation & paragraphs", padding=10)
        g_punct.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        g_punct.grid_columnconfigure(0, weight=1)

        self.e_comma_rate = LabeledEntry(g_punct, "Comma insertion rate (0..1)", width=10)
        self.e_max_commas = LabeledEntry(g_punct, "Max commas per sentence", width=10)
        self.e_comma_rate.grid(row=0, column=0, sticky="w", pady=4)
        self.e_max_commas.grid(row=1, column=0, sticky="w", pady=4)

        g_end = ttk.Frame(g_punct)
        ttk.Label(g_end, text="Sentence end punctuation weights").grid(row=0, column=0, sticky="w", columnspan=6, pady=(0, 4))
        self.e_w_period = LabeledEntry(g_end, "'.' weight", width=8)
        self.e_w_q = LabeledEntry(g_end, "'?' weight", width=8)
        self.e_w_ex = LabeledEntry(g_end, "'!' weight", width=8)
        self.e_w_period.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.e_w_q.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.e_w_ex.grid(row=1, column=2, sticky="w")
        g_end.grid(row=2, column=0, sticky="w", pady=6)

        self.cb_paras = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_punct, text="Enable paragraph breaks", variable=self.cb_paras,
            command=self._update_preview
        ).grid(row=3, column=0, sticky="w", pady=4)
        self.r_para_every = RangeRow(g_punct, "Paragraph break every N sentences", width=8)
        self.r_para_every.grid(row=4, column=0, sticky="w", pady=4)

        # Output group
        g_out = ttk.Labelframe(left, text="Output settings", padding=10)
        g_out.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        g_out.grid_columnconfigure(0, weight=1)

        self.out_dir = tk.StringVar(value="C:/temp")
        row_dir = ttk.Frame(g_out)
        ttk.Label(row_dir, text="Save folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.e_dir = ttk.Entry(row_dir, textvariable=self.out_dir, width=38)
        self.e_dir.grid(row=0, column=1, sticky="ew")
        ttk.Button(row_dir, text="Browse…", command=self._browse_dir).grid(row=0, column=2, sticky="w", padx=(8, 0))
        row_dir.grid_columnconfigure(1, weight=1)
        row_dir.grid(row=0, column=0, sticky="ew", pady=4)

        self.e_prefix = LabeledEntry(g_out, "Filename prefix", width=20)
        self.e_suffix = LabeledEntry(g_out, "Filename suffix", width=20)
        self.e_start_index = LabeledEntry(g_out, "Start number", width=10)
        self.e_pad = LabeledEntry(g_out, "Zero-pad width", width=10)
        self.e_ext = LabeledEntry(g_out, "Extension", width=10)
        self.e_seed = LabeledEntry(g_out, "Seed (optional)", width=20)

        self.e_prefix.grid(row=1, column=0, sticky="w", pady=4)
        self.e_suffix.grid(row=2, column=0, sticky="w", pady=4)
        self.e_start_index.grid(row=3, column=0, sticky="w", pady=4)
        self.e_pad.grid(row=4, column=0, sticky="w", pady=4)
        self.e_ext.grid(row=5, column=0, sticky="w", pady=4)
        self.e_seed.grid(row=6, column=0, sticky="w", pady=4)

        self.cb_overwrite = tk.BooleanVar(value=False)
        ttk.Checkbutton(g_out, text="Overwrite existing files", variable=self.cb_overwrite).grid(
            row=7, column=0, sticky="w", pady=(6, 4)
        )

        self.cb_export_json = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_out, text="Export JSON settings sidecar", variable=self.cb_export_json
        ).grid(row=8, column=0, sticky="w", pady=(8, 4))

        self.e_json_name = LabeledEntry(g_out, "Settings JSON filename", width=24)
        self.e_json_name.grid(row=9, column=0, sticky="w", pady=4)

        self.cb_json_filelist = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            g_out, text="Include generated file list in JSON", variable=self.cb_json_filelist
        ).grid(row=10, column=0, sticky="w", pady=4)

        self.cb_json_vocab = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            g_out, text="Include vocabularies in JSON (makes large settings files)", variable=self.cb_json_vocab
        ).grid(row=11, column=0, sticky="w", pady=4)

        # Buttons
        btns = ttk.Frame(left)
        ttk.Button(btns, text="Preview sample", command=self._update_preview).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Generate files", command=self._generate_files).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Reset defaults", command=self._reset_defaults).grid(row=0, column=2)
        btns.grid(row=7, column=0, sticky="w", pady=(4, 0))

        # ---- RIGHT: Preview + log
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ttk.Label(right, text="Preview", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.preview = ScrolledText(right, height=18, wrap="word")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=(6, 10))

        ttk.Label(right, text="Log", font=("TkDefaultFont", 11, "bold")).grid(row=2, column=0, sticky="w")
        self.log = ScrolledText(right, height=10, wrap="word")
        self.log.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        right.grid_rowconfigure(3, weight=1)

        watched = [
            self.e_num_files.entry, self.r_sentences.min_entry, self.r_sentences.max_entry,
            self.r_words.min_entry, self.r_words.max_entry,
            self.e_word_mean.entry, self.e_word_sd.entry,
            self.r_wordlen_bounds.min_entry, self.r_wordlen_bounds.max_entry,
            self.r_syllables.min_entry, self.r_syllables.max_entry,
            self.e_alphabet.entry,

            self.e_zipf_exp.entry, self.e_func_vocab.entry, self.e_cont_vocab.entry, self.e_ent_vocab.entry,
            self.r_ent_len.min_entry, self.r_ent_len.max_entry,
            self.e_ent_start_rate.entry, self.e_ent_noun_rate.entry,

            self.e_proper_rate.entry, self.e_caps_rate.entry,
            self.e_comma_rate.entry, self.e_max_commas.entry,
            self.e_w_period.entry, self.e_w_q.entry, self.e_w_ex.entry,
            self.r_para_every.min_entry, self.r_para_every.max_entry,

            self.e_prefix.entry, self.e_suffix.entry, self.e_start_index.entry,
            self.e_pad.entry, self.e_ext.entry, self.e_seed.entry,
            self.e_json_name.entry,
            self.e_dir,
        ]
        for widget in watched:
            widget.bind("<FocusOut>", lambda _e: self._update_preview())

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg.rstrip() + "\n")
        self.log.see("end")

    def _browse_dir(self) -> None:
        p = filedialog.askdirectory(title="Choose output folder")
        if p:
            self.out_dir.set(p)
            self._update_preview()

    def _reset_defaults(self) -> None:
        self.cfg = NoiseTextConfig()
        self._load_defaults_into_ui()
        self._update_preview()
        self._log("Reset to defaults.")

    def _load_defaults_into_ui(self) -> None:
        c = self.cfg
        self.e_num_files.set(c.num_files)
        self.r_sentences.set(c.sentences_min, c.sentences_max)
        self.r_words.set(c.words_min, c.words_max)

        self.e_word_mean.set(c.word_len_mean)
        self.e_word_sd.set(c.word_len_stdev)
        self.r_wordlen_bounds.set(c.word_len_min, c.word_len_max)

        self.gen_mode.set(c.generator_mode)
        self.cb_allow_double.set(c.allow_double_letters)
        self.r_syllables.set(c.syllables_min, c.syllables_max)
        self.e_alphabet.set(c.uniform_alphabet)

        self.cb_zipf.set(c.enable_zipf_reuse)
        self.e_zipf_exp.set(c.zipf_exponent)
        self.cb_pos_suffix.set(c.pos_like_suffixes)
        self.e_func_vocab.set(c.function_vocab_size)
        self.e_cont_vocab.set(c.content_vocab_size)
        self.e_ent_vocab.set(c.entity_vocab_size)
        self.r_ent_len.set(c.entity_tokens_min, c.entity_tokens_max)
        self.e_ent_start_rate.set(c.entity_sentence_start_rate)
        self.e_ent_noun_rate.set(c.entity_replace_noun_rate)

        self.cb_cap_start.set(c.capitalize_sentence_start)
        self.e_proper_rate.set(c.internal_proper_noun_rate)
        self.e_caps_rate.set(c.all_caps_rate)

        self.e_comma_rate.set(c.comma_rate)
        self.e_max_commas.set(c.max_commas_per_sentence)
        self.e_w_period.set(c.period_weight)
        self.e_w_q.set(c.question_weight)
        self.e_w_ex.set(c.exclaim_weight)

        self.cb_paras.set(c.enable_paragraphs)
        self.r_para_every.set(c.paragraph_break_min_sentences, c.paragraph_break_max_sentences)

        self.e_prefix.set(c.filename_prefix)
        self.e_suffix.set(c.filename_suffix)
        self.e_start_index.set(c.start_index)
        self.e_pad.set(c.zero_pad_width)
        self.e_ext.set(c.extension)
        self.cb_overwrite.set(c.overwrite_existing)
        self.e_seed.set(c.seed)

        self.cb_export_json.set(c.export_settings_json)
        self.e_json_name.set(c.settings_filename)
        self.cb_json_filelist.set(c.include_file_list_in_json)
        self.cb_json_vocab.set(c.include_vocab_in_json)

        if not self.out_dir.get().strip():
            self.out_dir.set(str(Path.cwd()))

        self._on_mode_change()
        self._on_zipf_toggle()

    def _on_mode_change(self) -> None:
        mode = self.gen_mode.get()
        if mode == "uniform":
            self.e_alphabet.entry.configure(state="normal")
        else:
            self.e_alphabet.entry.configure(state="disabled")

        if mode == "syllable":
            self.r_syllables.min_entry.configure(state="normal")
            self.r_syllables.max_entry.configure(state="normal")
        else:
            self.r_syllables.min_entry.configure(state="disabled")
            self.r_syllables.max_entry.configure(state="disabled")

        self._update_preview()

    def _on_zipf_toggle(self) -> None:
        enabled = bool(self.cb_zipf.get())
        state = "normal" if enabled else "disabled"
        for w in [
            self.e_zipf_exp.entry,
            self.e_func_vocab.entry, self.e_cont_vocab.entry, self.e_ent_vocab.entry,
            self.r_ent_len.min_entry, self.r_ent_len.max_entry,
            self.e_ent_start_rate.entry, self.e_ent_noun_rate.entry,
        ]:
            w.configure(state=state)

        self._update_preview()

    def _normalize_extension(self, ext: str) -> str:
        ext = ext.strip()
        if not ext:
            return ".txt"
        if not ext.startswith("."):
            ext = "." + ext
        return ext

    def _read_cfg_from_ui(self) -> NoiseTextConfig:
        c = NoiseTextConfig()

        c.num_files = self.e_num_files.get_int(min_value=1, max_value=1_000_000)
        c.sentences_min, c.sentences_max = self.r_sentences.get_int_range(min_value=1, max_value=1_000_000)
        c.words_min, c.words_max = self.r_words.get_int_range(min_value=1, max_value=1_000_000)

        c.word_len_mean = self.e_word_mean.get_float(min_value=1.0, max_value=200.0)
        c.word_len_stdev = self.e_word_sd.get_float(min_value=0.0, max_value=200.0)
        c.word_len_min, c.word_len_max = self.r_wordlen_bounds.get_int_range(min_value=1, max_value=500)

        c.generator_mode = self.gen_mode.get().strip()
        c.allow_double_letters = bool(self.cb_allow_double.get())
        c.syllables_min, c.syllables_max = self.r_syllables.get_int_range(min_value=1, max_value=20)
        c.uniform_alphabet = self.e_alphabet.get_str().strip() or "abcdefghijklmnopqrstuvwxyz"

        c.enable_zipf_reuse = bool(self.cb_zipf.get())
        c.zipf_exponent = self.e_zipf_exp.get_float(min_value=0.2, max_value=5.0)
        c.pos_like_suffixes = bool(self.cb_pos_suffix.get())

        c.function_vocab_size = self.e_func_vocab.get_int(min_value=10, max_value=200_000)
        c.content_vocab_size = self.e_cont_vocab.get_int(min_value=20, max_value=2_000_000)
        c.entity_vocab_size = self.e_ent_vocab.get_int(min_value=5, max_value=200_000)

        c.entity_tokens_min, c.entity_tokens_max = self.r_ent_len.get_int_range(min_value=1, max_value=10)
        c.entity_sentence_start_rate = self.e_ent_start_rate.get_float(min_value=0.0, max_value=1.0)
        c.entity_replace_noun_rate = self.e_ent_noun_rate.get_float(min_value=0.0, max_value=1.0)

        c.capitalize_sentence_start = bool(self.cb_cap_start.get())
        c.internal_proper_noun_rate = self.e_proper_rate.get_float(min_value=0.0, max_value=1.0)
        c.all_caps_rate = self.e_caps_rate.get_float(min_value=0.0, max_value=1.0)

        c.comma_rate = self.e_comma_rate.get_float(min_value=0.0, max_value=1.0)
        c.max_commas_per_sentence = self.e_max_commas.get_int(min_value=0, max_value=20)

        c.period_weight = self.e_w_period.get_float(min_value=0.0, max_value=1_000_000.0)
        c.question_weight = self.e_w_q.get_float(min_value=0.0, max_value=1_000_000.0)
        c.exclaim_weight = self.e_w_ex.get_float(min_value=0.0, max_value=1_000_000.0)

        c.enable_paragraphs = bool(self.cb_paras.get())
        c.paragraph_break_min_sentences, c.paragraph_break_max_sentences = self.r_para_every.get_int_range(min_value=1, max_value=1_000_000)

        c.filename_prefix = self.e_prefix.get_str()
        c.filename_suffix = self.e_suffix.get_str()
        c.start_index = self.e_start_index.get_int(min_value=0, max_value=1_000_000_000)
        c.zero_pad_width = self.e_pad.get_int(min_value=0, max_value=20)
        c.extension = self._normalize_extension(self.e_ext.get_str())
        c.overwrite_existing = bool(self.cb_overwrite.get())
        c.seed = self.e_seed.get_str().strip()

        c.export_settings_json = bool(self.cb_export_json.get())
        c.settings_filename = self.e_json_name.get_str().strip() or "dataset_settings.json"
        if not c.settings_filename.lower().endswith(".json"):
            c.settings_filename += ".json"
        c.include_file_list_in_json = bool(self.cb_json_filelist.get())
        c.include_vocab_in_json = bool(self.cb_json_vocab.get())

        if c.word_len_min > c.word_len_max:
            raise ValueError("Word length bounds are invalid.")
        if c.word_len_mean < c.word_len_min or c.word_len_mean > c.word_len_max:
            raise ValueError("Average word length should fall within the word length bounds.")
        if c.generator_mode not in {"syllable", "letterfreq", "uniform"}:
            raise ValueError("Generator mode is invalid.")
        if c.syllables_min > c.syllables_max:
            raise ValueError("Syllables per word bounds are invalid.")

        if c.generator_mode == "uniform":
            cleaned = "".join(ch for ch in c.uniform_alphabet if ch.isprintable() and not ch.isspace())
            if len(cleaned) < 2:
                raise ValueError("Alphabet must contain at least 2 printable non-space characters.")
            c.uniform_alphabet = cleaned

        return c

    def _make_generator(self) -> NoiseTextGenerator:
        cfg = self._read_cfg_from_ui()
        if cfg.seed:
            random.seed(cfg.seed)
        else:
            random.seed(None)
        return NoiseTextGenerator(cfg)

    def _update_preview(self) -> None:
        try:
            gen = self._make_generator()
            txt = gen.generate_document()
            self.preview.delete("1.0", "end")
            self.preview.insert("end", txt)
        except Exception as e:
            self._log(f"[Preview error] {e}")

    def _next_available_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        for k in range(1, 10000):
            p = parent / f"{stem}_{k}{suffix}"
            if not p.exists():
                return p
        return parent / f"{stem}_{random.randint(10000, 99999)}{suffix}"

    def _generate_files(self) -> None:
        try:
            cfg = self._read_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Invalid settings", str(e))
            return

        out = Path(self.out_dir.get().strip() or ".").expanduser().resolve()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Cannot create output folder", f"{out}\n\n{e}")
            return

        if cfg.seed:
            random.seed(cfg.seed)
        else:
            random.seed(None)

        gen = NoiseTextGenerator(cfg)

        pad = max(0, cfg.zero_pad_width)
        start = cfg.start_index

        written = 0
        planned = cfg.num_files
        created_files: List[str] = []

        self._log(f"Output folder: {out}")
        self._log(f"Generating {planned} file(s)…")

        for i in range(planned):
            idx = start + i
            num = str(idx).zfill(pad) if pad > 0 else str(idx)
            fname = f"{cfg.filename_prefix}{num}{cfg.filename_suffix}{cfg.extension}"
            path = out / fname

            if path.exists() and not cfg.overwrite_existing:
                messagebox.showerror(
                    "File exists",
                    f"Refusing to overwrite existing file:\n\n{path}\n\n"
                    "Enable 'Overwrite existing files' or change naming settings."
                )
                self._log(f"Aborted: file exists and overwrite disabled: {path}")
                return

            text = gen.generate_document()
            try:
                path.write_text(text, encoding="utf-8", errors="strict")
            except Exception as e:
                messagebox.showerror("Write failed", f"Could not write:\n\n{path}\n\n{e}")
                self._log(f"Write failed: {path} ({e})")
                return

            created_files.append(fname)
            written += 1

        if cfg.export_settings_json:
            settings_path = out / cfg.settings_filename
            if settings_path.exists() and not cfg.overwrite_existing:
                settings_path = self._next_available_path(settings_path)

            payload: Dict[str, object] = {
                "tool": "Noise Text Dataset Builder",
                "tool_version": self.TOOL_VERSION,
                "created_at_local": _dt.datetime.now().isoformat(timespec="seconds"),
                "python": sys.version.replace("\n", " "),
                "config": asdict(cfg),
            }

            if cfg.enable_zipf_reuse:
                payload["derived_vocab_sizes"] = gen.derived_sizes()

            if cfg.include_file_list_in_json:
                payload["generated_files"] = created_files

            if cfg.include_vocab_in_json and cfg.enable_zipf_reuse:
                payload["vocabularies"] = {k: gen.lex[k].vocab() for k in sorted(gen.lex.keys())}

            try:
                settings_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                self._log(f"Wrote settings JSON: {settings_path.name}")
            except Exception as e:
                messagebox.showerror("Settings JSON write failed", f"Could not write:\n\n{settings_path}\n\n{e}")
                self._log(f"Settings JSON write failed: {settings_path} ({e})")
                return

        self._log(f"Done. Wrote {written} file(s).")
        messagebox.showinfo("Complete", f"Wrote {written} file(s) to:\n{out}")

        self._update_preview()


def main() -> int:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    _app = App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())