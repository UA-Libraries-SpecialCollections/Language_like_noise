#!/usr/bin/env python3
"""
Noise Text Dataset Builder (Tkinter GUI) — Python 3.10

Creates a set of .txt files that look like structured natural-language writing:
sentences and paragraphs with punctuation and capitalization — but every "word"
is a meaningless, procedurally generated string.

No external dependencies (stdlib only).
"""

from __future__ import annotations

import math
import os
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText


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


def clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def weighted_choice(items: List[str], weights: List[float]) -> str:
    # random.choices is fine, but keep it explicit for clarity
    return random.choices(items, weights=weights, k=1)[0]


def sample_word_length(mean: float, stdev: float, min_len: int, max_len: int) -> int:
    if stdev <= 0:
        return clamp_int(int(round(mean)), min_len, max_len)

    # Truncated normal sampling (simple rejection); bounded and fast for small ranges.
    for _ in range(50):
        v = random.gauss(mean, stdev)
        n = int(round(v))
        if min_len <= n <= max_len:
            return n
    # Fallback if rejection failed
    return clamp_int(int(round(mean)), min_len, max_len)


def generate_word_uniform(length: int, alphabet: str, allow_double: bool = True) -> str:
    if length <= 0:
        return ""
    chars = []
    prev = ""
    for _ in range(length):
        c = random.choice(alphabet)
        if not allow_double and c == prev:
            # try a couple times to avoid doubles
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
    # Build 1..N syllables then trim/pad to match target length as closely as possible.
    syllables = random.randint(min_syllables, max_syllables)
    parts: List[str] = []
    prev = ""
    for _ in range(syllables):
        onset = random.choice(SYLLABLE_ONSETS)
        nucleus = random.choice(SYLLABLE_NUCLEI)
        coda = random.choice(SYLLABLE_CODAS)
        s = onset + nucleus + coda

        if not allow_double and prev and s and prev[-1] == s[0]:
            # soften double boundary
            s = s[1:] if len(s) > 1 else s

        parts.append(s)
        prev = s

    word = "".join(parts)
    if not word:
        word = "a"

    if len(word) == target_len:
        return word

    if len(word) > target_len:
        # Prefer to trim from the end
        return word[:target_len]

    # Pad by appending vowel/consonant to reach target length
    vowels = "aeiouy"
    consonants = "bcdfghjklmnpqrstvwxz"
    while len(word) < target_len:
        # alternate a little to keep word-like feel
        last = word[-1]
        if last in vowels:
            word += random.choice(consonants)
        else:
            word += random.choice(vowels)
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

    # sentence styling
    capitalize_sentence_start: bool = True
    internal_proper_noun_rate: float = 0.03  # chance a random word is Title Case
    all_caps_rate: float = 0.005  # chance a random word is ALL CAPS

    # punctuation / structure
    comma_rate: float = 0.12  # chance to insert comma(s) into a sentence
    max_commas_per_sentence: int = 2

    period_weight: float = 0.86
    question_weight: float = 0.09
    exclaim_weight: float = 0.05

    paragraph_break_min_sentences: int = 3
    paragraph_break_max_sentences: int = 6
    enable_paragraphs: bool = True

    # output
    filename_prefix: str = "noise_"
    filename_suffix: str = ""
    start_index: int = 1
    zero_pad_width: int = 4
    extension: str = ".txt"
    overwrite_existing: bool = False

    seed: str = ""  # empty => random


class NoiseTextGenerator:
    def __init__(self, cfg: NoiseTextConfig):
        self.cfg = cfg

    def _gen_word(self, length: int) -> str:
        cfg = self.cfg
        if cfg.generator_mode == "uniform":
            alphabet = cfg.uniform_alphabet.strip() or "abcdefghijklmnopqrstuvwxyz"
            return generate_word_uniform(length, alphabet=alphabet, allow_double=cfg.allow_double_letters)
        if cfg.generator_mode == "letterfreq":
            return generate_word_letterfreq(length, allow_double=cfg.allow_double_letters)
        # syllable default
        return generate_word_syllable(
            target_len=length,
            min_syllables=cfg.syllables_min,
            max_syllables=cfg.syllables_max,
            allow_double=cfg.allow_double_letters,
        )

    def _sentence_end_punct(self) -> str:
        cfg = self.cfg
        items = [".", "?", "!"]
        weights = [max(0.0, cfg.period_weight), max(0.0, cfg.question_weight), max(0.0, cfg.exclaim_weight)]
        if sum(weights) <= 0:
            return "."
        return weighted_choice(items, weights)

    def _maybe_insert_commas(self, words: List[str]) -> List[str]:
        cfg = self.cfg
        if len(words) < 6:
            return words

        if random.random() > cfg.comma_rate:
            return words

        # Choose 1..max commas, bias toward 1
        k = 1 if cfg.max_commas_per_sentence <= 1 else random.randint(1, cfg.max_commas_per_sentence)
        positions = set()
        # avoid first and last word
        while len(positions) < k:
            positions.add(random.randint(2, len(words) - 2))

        new_words = []
        for i, w in enumerate(words, start=1):
            if i in positions:
                new_words.append(w + ",")
            else:
                new_words.append(w)
        return new_words

    def generate_sentence(self) -> str:
        cfg = self.cfg
        n_words = random.randint(cfg.words_min, cfg.words_max)

        words: List[str] = []
        for i in range(n_words):
            wl = sample_word_length(cfg.word_len_mean, cfg.word_len_stdev, cfg.word_len_min, cfg.word_len_max)
            w = self._gen_word(wl)

            # occasional "proper noun" style capitalization, but meaningless content
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

    def generate_document(self) -> str:
        cfg = self.cfg
        n_sentences = random.randint(cfg.sentences_min, cfg.sentences_max)

        sentences = [self.generate_sentence() for _ in range(n_sentences)]

        if not cfg.enable_paragraphs or n_sentences < 6:
            return " ".join(sentences) + "\n"

        # paragraph breaks every X sentences (randomized in a range)
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
    """Label + entry, with optional validation and a 'get' helper."""
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
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master.title("Noise Text Dataset Builder")
        self.master.geometry("980x720")
        self.master.minsize(900, 650)

        self.cfg = NoiseTextConfig()

        self._build_ui()
        self._load_defaults_into_ui()
        self._update_preview()

    def _build_ui(self) -> None:
        # Layout: left controls (scrollable-ish) + right preview/log
        self.grid(row=0, column=0, sticky="nsew")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        left = ttk.Frame(paned, padding=12)
        right = ttk.Frame(paned, padding=12)
        paned.add(left, weight=1)
        paned.add(right, weight=2)

        # ---- LEFT: Controls
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
        g_gen = ttk.Labelframe(left, text="Word generator", padding=10)
        g_gen.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        g_gen.grid_columnconfigure(0, weight=1)

        self.gen_mode = tk.StringVar(value="syllable")
        modes = ttk.Frame(g_gen)
        ttk.Label(modes, text="Mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Radiobutton(modes, text="Syllable-based (most word-like)", variable=self.gen_mode, value="syllable",
                        command=self._on_mode_change).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(modes, text="English letter-frequency", variable=self.gen_mode, value="letterfreq",
                        command=self._on_mode_change).grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(modes, text="Uniform random letters", variable=self.gen_mode, value="uniform",
                        command=self._on_mode_change).grid(row=2, column=1, sticky="w")
        modes.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.cb_allow_double = tk.BooleanVar(value=True)
        ttk.Checkbutton(g_gen, text="Allow doubled letters (e.g., 'tt')", variable=self.cb_allow_double,
                        command=self._update_preview).grid(row=1, column=0, sticky="w", pady=4)

        self.r_syllables = RangeRow(g_gen, "Syllables per word", width=8)
        self.r_syllables.grid(row=2, column=0, sticky="w", pady=4)

        self.e_alphabet = LabeledEntry(g_gen, "Alphabet (uniform mode)", width=30)
        self.e_alphabet.grid(row=3, column=0, sticky="w", pady=4)

        # Styling group
        g_style = ttk.Labelframe(left, text="Sentence styling", padding=10)
        g_style.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        g_style.grid_columnconfigure(0, weight=1)

        self.cb_cap_start = tk.BooleanVar(value=True)
        ttk.Checkbutton(g_style, text="Capitalize first word of each sentence", variable=self.cb_cap_start,
                        command=self._update_preview).grid(row=0, column=0, sticky="w", pady=4)

        self.e_proper_rate = LabeledEntry(g_style, "Title-Case word rate (0..1)", width=10)
        self.e_caps_rate = LabeledEntry(g_style, "ALL-CAPS word rate (0..1)", width=10)
        self.e_proper_rate.grid(row=1, column=0, sticky="w", pady=4)
        self.e_caps_rate.grid(row=2, column=0, sticky="w", pady=4)

        # Punctuation group
        g_punct = ttk.Labelframe(left, text="Punctuation & paragraphs", padding=10)
        g_punct.grid(row=4, column=0, sticky="ew", pady=(0, 10))
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
        ttk.Checkbutton(g_punct, text="Enable paragraph breaks", variable=self.cb_paras,
                        command=self._update_preview).grid(row=3, column=0, sticky="w", pady=4)
        self.r_para_every = RangeRow(g_punct, "Paragraph break every N sentences", width=8)
        self.r_para_every.grid(row=4, column=0, sticky="w", pady=4)

        # Output group
        g_out = ttk.Labelframe(left, text="Output settings", padding=10)
        g_out.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        g_out.grid_columnconfigure(0, weight=1)

        self.out_dir = tk.StringVar(value="")
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

        # Buttons
        btns = ttk.Frame(left)
        ttk.Button(btns, text="Preview sample", command=self._update_preview).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Generate files", command=self._generate_files).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Reset defaults", command=self._reset_defaults).grid(row=0, column=2)
        btns.grid(row=6, column=0, sticky="w", pady=(4, 0))

        # ---- RIGHT: Preview + log
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ttk.Label(right, text="Preview (one generated document)", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.preview = ScrolledText(right, height=18, wrap="word")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=(6, 10))

        ttk.Label(right, text="Log", font=("TkDefaultFont", 11, "bold")).grid(row=2, column=0, sticky="w")
        self.log = ScrolledText(right, height=10, wrap="word")
        self.log.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        right.grid_rowconfigure(3, weight=1)

        # Live preview updates on most text variables losing focus
        for widget in [
            self.e_num_files.entry, self.r_sentences.min_entry, self.r_sentences.max_entry,
            self.r_words.min_entry, self.r_words.max_entry,
            self.e_word_mean.entry, self.e_word_sd.entry,
            self.r_wordlen_bounds.min_entry, self.r_wordlen_bounds.max_entry,
            self.r_syllables.min_entry, self.r_syllables.max_entry,
            self.e_alphabet.entry,
            self.e_proper_rate.entry, self.e_caps_rate.entry,
            self.e_comma_rate.entry, self.e_max_commas.entry,
            self.e_w_period.entry, self.e_w_q.entry, self.e_w_ex.entry,
            self.r_para_every.min_entry, self.r_para_every.max_entry,
            self.e_prefix.entry, self.e_suffix.entry, self.e_start_index.entry,
            self.e_pad.entry, self.e_ext.entry, self.e_seed.entry,
            self.e_dir,
        ]:
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

        # sensible default output dir
        if not self.out_dir.get().strip():
            self.out_dir.set(str(Path.cwd()))

        self._on_mode_change()

    def _on_mode_change(self) -> None:
        # Enable/disable mode-specific controls
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

    def _read_cfg_from_ui(self) -> NoiseTextConfig:
        c = NoiseTextConfig()

        c.num_files = self.e_num_files.get_int(min_value=1, max_value=1_000_000)
        c.sentences_min, c.sentences_max = self.r_sentences.get_int_range(min_value=1, max_value=1_000_000)
        c.words_min, c.words_max = self.r_words.get_int_range(min_value=1, max_value=1_000_000)

        c.word_len_mean = self.e_word_mean.get_float(min_value=1.0, max_value=100.0)
        c.word_len_stdev = self.e_word_sd.get_float(min_value=0.0, max_value=100.0)
        c.word_len_min, c.word_len_max = self.r_wordlen_bounds.get_int_range(min_value=1, max_value=1000)

        c.generator_mode = self.gen_mode.get().strip()
        c.allow_double_letters = bool(self.cb_allow_double.get())
        c.syllables_min, c.syllables_max = self.r_syllables.get_int_range(min_value=1, max_value=20)
        c.uniform_alphabet = self.e_alphabet.get_str().strip() or "abcdefghijklmnopqrstuvwxyz"

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

        # Additional cross-checks:
        if c.word_len_min > c.word_len_max:
            raise ValueError("Word length bounds are invalid.")
        if c.word_len_mean < c.word_len_min or c.word_len_mean > c.word_len_max:
            # Not strictly required, but helps avoid surprising truncation
            raise ValueError("Average word length should fall within the word length bounds.")
        if c.generator_mode not in {"syllable", "letterfreq", "uniform"}:
            raise ValueError("Generator mode is invalid.")
        if c.syllables_min > c.syllables_max:
            raise ValueError("Syllables per word bounds are invalid.")

        # Uniform alphabet sanity
        if c.generator_mode == "uniform":
            # Keep only printable, non-space chars
            cleaned = "".join(ch for ch in c.uniform_alphabet if ch.isprintable() and not ch.isspace())
            if len(cleaned) < 2:
                raise ValueError("Alphabet must contain at least 2 printable non-space characters.")
            c.uniform_alphabet = cleaned

        return c

    def _normalize_extension(self, ext: str) -> str:
        ext = ext.strip()
        if not ext:
            return ".txt"
        if not ext.startswith("."):
            ext = "." + ext
        return ext

    def _make_generator(self) -> NoiseTextGenerator:
        cfg = self._read_cfg_from_ui()

        # Seed handling
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
            # Keep old preview, but show error in log
            self._log(f"[Preview error] {e}")

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

        # Seed handling
        if cfg.seed:
            random.seed(cfg.seed)
        else:
            random.seed(None)

        gen = NoiseTextGenerator(cfg)

        # Determine filenames
        pad = max(0, cfg.zero_pad_width)
        start = cfg.start_index

        written = 0
        planned = cfg.num_files
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

            written += 1

        self._log(f"Done. Wrote {written} file(s).")
        messagebox.showinfo("Complete", f"Wrote {written} file(s) to:\n{out}")

        # Refresh preview to reflect end state / current seed settings
        self._update_preview()


def main() -> int:
    root = tk.Tk()
    try:
        # nicer native-ish look on some platforms
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
