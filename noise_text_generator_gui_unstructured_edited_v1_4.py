#!/usr/bin/env python3

# Uses Python 3.10 :  C:\Python310>python.exe "S:\Digital Projects\Dev\language_like_noise_text_gen\noise_text_generator_gui_unstructured.py"
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
optional real-English dictionary-word mode
Unstructured character noise mode

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
import uuid
from collections import Counter
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

# Curated real-word lexicons for dictionary mode. These keep the tool self-contained
# while ensuring every generated token is a correctly spelled English word.
DICTIONARY_DETERMINERS = """
a an another any both each either enough every few fewer less little many more most much
neither no one other our several some such that the their these this those whatever which
whichever whose your my her his its all certain various enough plenty
""".split()

DICTIONARY_PREPOSITIONS = """
about above across after against along amid among around as at before behind below beneath
beside besides between beyond by despite down during except for from in inside into like near
of off on onto out outside over past since through throughout till to toward under underneath
until unto up upon via with within without
""".split()

DICTIONARY_CONJUNCTIONS = """
and although as because before but either if lest nor once only or provided since so though
unless until when whenever whereas whether while yet
""".split()

DICTIONARY_PRONOUNS = """
all another anybody anyone anything both each either everybody everyone everything
he her herself him himself i it itself many me mine most much myself neither nobody none
nothing one other others ours ourselves several she some somebody someone something that
theirs them themselves these they this those us we what whatever which whichever who whoever
whom whose you yours yourself yourselves
""".split()

DICTIONARY_NOUNS = """
answer apple area art bird body book bread bridge brother building business camera camp candle
car castle cat cause child circle city cloud coast color country course day daughter detail
door dream earth engine evening family farmer field fire flower forest friend garden gate girl
glass group hall hand harbor hat heart hill history home horse hour house idea island issue
journey kitchen lake leaf letter library light line machine market meadow memory minute mirror
money month morning mountain music night number ocean office paper park path person picture
place plan planet plant point pond power problem queen rain river road room rule school sea
shadow ship sky snow sound spring star stone story street summer sun table task teacher thing
thunder time tower train tree valley value village voice wall water way window winter woman
world writer year actor agency air animal army aunt balance bank base basket beach bell berry
boat bone border bottle branch breeze brook cabin cake capital captain carpet cart cell chain
chance chapter chest class clock college corner cousin creek crowd crown current curve damage
depth desert diamond dinner district doctor drawing dust effort energy estate event example
fabric fact feather festival figure film floor flour fortune frame future game gift grain grass
ground guest guide harmony harvest holiday hope hotel image iron judge journal key kingdom
ladder language law legend lesson level limit map metal method moment motor nation note object
order page palace pattern people pepper phrase piano pillow pilot poem police policy prayer
price pride prize process rabbit recipe region respect review rhythm ribbon science season seed
shape shelter signal silver sister skill smoke song spirit square station stream strength string
success sugar system talent temple theory ticket travel treasure union vision volume weather week
whisper wonder worker yard youth
""".split()

DICTIONARY_VERBS = """
accept admire admit answer appear arrive ask balance become begin belong borrow break bring
build carry catch change choose climb collect consider continue cook create cross dance decide
deliver discover discuss draw drink drive embrace emerge enjoy enter examine exist explore face
fall follow gather glance grow handle hear help imagine improve include influence invent join
jump keep know laugh learn leave lift listen live look love make manage measure meet move notice
observe open paint pass pay plan play prefer prepare protect prove reach read realize remember
remove repeat reply rest return rise roll run search seem serve settle share shine sing sit
sleep smile solve speak stand start stay step stop study succeed suggest support take talk teach
think travel turn understand use visit wait walk wander watch whisper win work write act add
allow announce arrange awaken bake bend blink bloom boil breathe celebrate compare connect cover
dream earn encourage exercise fade fill flow fly forgive freeze glow guard happen hide honor
hurry identify inspire invite knock lean mark mend offer pause perform point pour press promise
publish question race recover reflect refuse relax rescue reveal sail shake shout sort spend
spread stretch surprise survive thank touch trust unfold wash wave wonder
""".split()

DICTIONARY_ADJECTIVES = """
able active ancient bright broken calm careful certain clear clever close cold common complex
curious daily dark distant eager early easy empty equal fair familiar famous final fine formal
free fresh gentle golden grand green happy heavy hidden honest humble ideal inner kind large
late light lively local lonely long loose lucky modern narrow natural nearby nervous new noble
normal open patient plain polite proud quick quiet rare ready real recent remote rich rough
royal safe secret serious sharp short silent simple small smooth soft solid special steady still
strange sudden sweet tall tender tiny tired true useful vast warm weary whole wild wise yellow
young actual alert brave brief broad busy central chief classic clean cloudy coastal creative
crisp deep direct eastern electric elegant exact faint fertile firm flexible fragile funny global
graceful gray healthy helpful hollow human hungry icy immense inland joyful level major minor
misty mobile muddy neat northern odd perfect pink pleasant precious prime private public rapid
raw rural shallow shy sleepy spare square stable steep stormy sturdy subtle sunny sure urban
varied vivid western wooden worthy
""".split()

DICTIONARY_ADVERBS = """
abruptly almost already always calmly carefully certainly clearly closely daily eagerly easily
enough eventually exactly finally gently gladly greatly happily hardly honestly kindly likely
loosely nearly never often openly partly politely promptly quickly quietly rarely really safely
seriously sharply silently simply slowly softly soon steadily strangely suddenly surely tenderly
truly unexpectedly usually warmly widely wisely yesterday
""".split()


def unique_words(words: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for word in words:
        token = (word or "").strip().lower()
        if token.isalpha() and token not in seen:
            seen.add(token)
            out.append(token)
    return out


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
    num_files: int = 250
    sentences_min: int = 100
    sentences_max: int = 250
    words_min: int = 12
    words_max: int = 20

    # word length distribution (English-ish defaults)
    word_len_mean: float = 4.7
    word_len_stdev: float = 1.8
    word_len_min: int = 2
    word_len_max: int = 12

    # generator mode
    generator_mode: str = "syllable"  # "syllable" | "letterfreq" | "uniform" | "dictionary" | "unstructured"
    uniform_alphabet: str = "abcdefghijklmnopqrstuvwxyz"
    allow_double_letters: bool = True

    # unstructured mode (non-language-like stream)
    unstructured_min_chars: int = 2500
    unstructured_max_chars: int = 8000
    unstructured_pool: str = string.ascii_letters + string.digits + string.punctuation
    unstructured_weight_alnum: float = 0.4
    unstructured_weight_punct: float = 0.3
    unstructured_weight_space: float = 0.1
    unstructured_weight_newline: float = 0.1
    unstructured_max_run: int = 4
    unstructured_allow_tabs: bool = False
    unstructured_tab_weight: float = 0.02

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


@dataclass
class TelephoneConfig:
    """Configuration for the Telephone Tree (cascading summaries) dataset method.

    This mode starts from meaningful ground-truth texts ("roots") and generates a branching tree of
    progressively shorter summaries, optionally alongside a "control" condition where each hop is
    summarized directly from the root (flat broadcast), following the paradigm from:

        Horta Ribeiro, Gligorić, West — "Message Distortion in Information Cascades" (WWW 2019)

    The builder enforces explicit acceptance bands for semantic similarity and lexical overlap
    between parent and child, enabling controlled semantic + lexical drift.
    """

    # ----------------------------- Seed texts -----------------------------
    seed_source_mode: str = "folder"          # "folder" | "file"
    seed_path: str = ""                      # folder path or file path
    seed_split_mode: str = "whole_file"      # "whole_file" | "paragraphs" | "fixed_chunks"
    fixed_chunk_chars: int = 2000            # only used when seed_split_mode == "fixed_chunks"
    max_roots: int = 20
    shuffle_roots: bool = False

    # ------------------------ Cascade / control setup ----------------------
    include_control: bool = True
    control_children_per_hop: int = 1

    depth: int = 5                           # number of hops
    branching_factor: int = 2                # children per node in cascade
    max_samples_total: int = 5000            # hard cap across roots + conditions
    expansion_strategy: str = "bfs"          # "bfs" | "dfs" | "random"

    # ------------------------- Length schedule (per hop) -------------------
    length_schedule_mode: str = "mdic"       # "mdic" | "geometric" | "custom"
    geometric_first_target: int = 1000       # hop-1 target chars for geometric schedule
    geometric_ratio: float = 0.5             # multiply each hop by this factor
    custom_targets_csv: str = "1000,500,250,125,64"

    slack_mode: str = "mdic"                 # "mdic" | "percent" | "fixed"
    slack_percent: float = 0.05              # for percent slack
    slack_fixed: int = 50                    # for fixed slack

    min_target_len: int = 64                 # don't shrink below this

    # -------------------- Drift acceptance bands (parent->child) -----------
    band_schedule_mode: str = "constant"     # "constant" | "linear"

    # Semantic similarity band (cosine similarity). Linear schedule interpolates start->end by hop.
    s_min_start: float = 0.70
    s_max_start: float = 0.95
    s_min_end: float = 0.65
    s_max_end: float = 0.90

    # Lexical overlap band (Jaccard over content tokens). Linear schedule interpolates start->end by hop.
    l_min_start: float = 0.15
    l_max_start: float = 0.65
    l_min_end: float = 0.05
    l_max_end: float = 0.35

    max_attempts_per_child: int = 25
    max_ngram_copy_ratio: float = 0.20       # word 4-gram copy ratio (0..1)

    # Similarity backend for the semantic band
    semantic_backend: str = "tfidf"          # "tfidf" | "sbert"

    # Dedupe threshold using RapidFuzz ratio (0..100). 100 = exact-only.
    dedupe_threshold: float = 96.0

    # ------------------------------- Export -------------------------------
    export_jsonl: bool = True
    jsonl_filename: str = f"telephone_tree_{date_val}.jsonl"
    export_txt_nodes: bool = False





# ---------------------------- Generator engine ----------------------------

class NoiseTextGenerator:
    def __init__(self, cfg: NoiseTextConfig):
        self.cfg = cfg
        self.lex: Dict[str, ZipfSampler] = {}
        self._derived_sizes: Dict[str, int] = {}
        self.dictionary_pools: Dict[str, List[str]] = {}
        self.dictionary_len_index: Dict[str, Dict[int, List[str]]] = {}

        if cfg.generator_mode == "dictionary":
            self._init_dictionary_pools()

        if cfg.enable_zipf_reuse and cfg.generator_mode != "unstructured":
            self._init_zipf_lexicons()

    # ----- dictionary helpers -----

    def _init_dictionary_pools(self) -> None:
        raw_pools: Dict[str, List[str]] = {
            "DET": DICTIONARY_DETERMINERS,
            "PREP": DICTIONARY_PREPOSITIONS,
            "CONJ": DICTIONARY_CONJUNCTIONS,
            "PRON": DICTIONARY_PRONOUNS,
            "NOUN": DICTIONARY_NOUNS,
            "VERB": DICTIONARY_VERBS,
            "ADJ": DICTIONARY_ADJECTIVES,
            "ADV": DICTIONARY_ADVERBS,
        }

        min_len = max(1, int(self.cfg.word_len_min))
        max_len = max(min_len, int(self.cfg.word_len_max))

        for key, words in raw_pools.items():
            full_pool = unique_words(words)
            filtered_pool = [w for w in full_pool if min_len <= len(w) <= max_len]
            pool = filtered_pool or full_pool or ["word"]
            self.dictionary_pools[key] = pool

            by_len: Dict[int, List[str]] = {}
            for w in pool:
                by_len.setdefault(len(w), []).append(w)
            self.dictionary_len_index[key] = by_len

        entity_parts = unique_words(self.dictionary_pools["ADJ"] + self.dictionary_pools["NOUN"])
        if not entity_parts:
            entity_parts = ["word"]

        content_words = unique_words(
            self.dictionary_pools["NOUN"]
            + self.dictionary_pools["VERB"]
            + self.dictionary_pools["ADJ"]
            + self.dictionary_pools["ADV"]
        )
        if not content_words:
            content_words = ["word"]

        for key, pool in {"ENTITY": entity_parts, "CONTENT": content_words}.items():
            self.dictionary_pools[key] = pool
            by_len: Dict[int, List[str]] = {}
            for w in pool:
                by_len.setdefault(len(w), []).append(w)
            self.dictionary_len_index[key] = by_len

    def _dictionary_word_from_pool(self, pool_key: str, target_len: Optional[int] = None) -> str:
        pool = self.dictionary_pools.get(pool_key) or self.dictionary_pools.get("CONTENT") or ["word"]
        if target_len is None:
            return random.choice(pool)

        by_len = self.dictionary_len_index.get(pool_key, {})
        max_radius = max(2, self.cfg.word_len_max - self.cfg.word_len_min + 4)
        for radius in range(0, max_radius + 1):
            candidates: List[str] = []
            lo = target_len - radius
            hi = target_len + radius
            if lo in by_len:
                candidates.extend(by_len[lo])
            if radius > 0 and hi in by_len:
                candidates.extend(by_len[hi])
            if candidates:
                return random.choice(candidates)
        return random.choice(pool)

    def _dictionary_word_for_pos(self, pos: str, target_len: Optional[int] = None) -> str:
        pool_key = pos if pos in self.dictionary_pools else "CONTENT"
        return self._dictionary_word_from_pool(pool_key, target_len=target_len)

    # ----- base word creation -----

    def _base_word(self, length: int) -> str:
        cfg = self.cfg
        if cfg.generator_mode == "dictionary":
            return self._dictionary_word_for_pos("CONTENT", target_len=length)
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

        if cfg.generator_mode == "dictionary":
            tok = self._dictionary_word_for_pos(pos, target_len=target)
            tok = "".join(ch for ch in tok if ch.isprintable() and not ch.isspace())
            return tok or "word"

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
        if self.cfg.generator_mode == "dictionary":
            pool = list(self.dictionary_pools.get(pos) or self.dictionary_pools.get("CONTENT") or ["word"])
            random.shuffle(pool)
            if title_case:
                pool = [maybe_capitalize(tok, "title") for tok in pool]
            if size > 0:
                pool = pool[:size]
            return pool or [maybe_capitalize("word", "title") if title_case else "word"]

        vocab: set[str] = set()
        attempts = 0
        # avoid infinite loops if constraints are too tight
        max_attempts = max(2000, size * 60)

        while len(vocab) < size and attempts < max_attempts:
            attempts += 1
            tok = self._make_pos_token(pos)
            if title_case:
                tok = maybe_capitalize(tok, "title")
            # basic cleanliness
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

        # Bias entity length slightly toward 2 words if possible
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
        self._derived_sizes = {}

        for pos in ["DET", "PREP", "CONJ", "PRON", "NOUN", "VERB", "ADJ", "ADV"]:
            vocab = self._build_vocab(pos, sizes[pos])
            self.lex[pos] = ZipfSampler(vocab, exponent=cfg.zipf_exponent)
            self._derived_sizes[pos] = len(vocab)

        entities = self._build_entity_phrases(sizes["ENTITY"])
        self.lex["ENTITY"] = ZipfSampler(entities, exponent=cfg.zipf_exponent)
        self._derived_sizes["ENTITY"] = len(entities)

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
        # Insert comma after word i (0-index i). Avoid first/last and protected positions.
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
        """
        Simple POS-ish Markov transitions to make output look grammatical-ish.
        Returns next POS, or "END".
        """
        # Base transition table
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
        # Safety fallback in case lexicons weren't initialized
        if pos in self.lex:
            return self.lex[pos].sample()
        # Fallback to base word generation (non-zipf)
        wl = sample_word_length(self.cfg.word_len_mean, self.cfg.word_len_stdev, self.cfg.word_len_min, self.cfg.word_len_max)
        return self._base_word(wl)

    def generate_sentence_zipf(self) -> str:
        cfg = self.cfg
        target_words = random.randint(cfg.words_min, cfg.words_max)

        words: List[str] = []
        protect_after: List[bool] = []  # True => avoid comma after this token

        # Optionally force entity at start
        prev = "START"
        if random.random() < cfg.entity_sentence_start_rate:
            phrase = self._zipf_token_for_pos("ENTITY")
            parts = phrase.split(" ")
            for j, p in enumerate(parts):
                words.append(p)
                protect_after.append(j < len(parts) - 1)
            prev = "ENTITY"

        # Generate until we hit target, then try to stop at a reasonable boundary
        max_soft = cfg.words_max + 8  # allow a little overshoot to land on an "endable" POS
        last_pos = prev

        while len(words) < target_words:
            pos = self._next_pos(last_pos)

            if pos == "END":
                if len(words) >= cfg.words_min:
                    break
                # If too short, keep going with a noun-ish continuation
                pos = "NOUN"

            # Replace some noun slots with entities
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

        # Try to end on a sensible POS if we're still in an awkward state
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

        # Hard trim if way too long
        if len(words) > max_soft:
            words = words[:max_soft]
            protect_after = protect_after[:max_soft]

        # Extra casing noise on non-entity tokens
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
            # Only title-case if not already entity/proper
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

    def generate_unstructured_document(self) -> str:
        """Generate a non-language-like stream of characters, punctuation, and whitespace."""
        cfg = self.cfg
        lo = max(0, int(cfg.unstructured_min_chars))
        hi = max(lo, int(cfg.unstructured_max_chars))
        target = random.randint(lo, hi) if hi > lo else lo

        # Pool provided by user is for non-whitespace; whitespace/newlines are inserted separately.
        pool = "".join(ch for ch in (cfg.unstructured_pool or "") if ch.isprintable() and not ch.isspace())
        if not pool:
            pool = string.ascii_letters + string.digits + string.punctuation

        alnum_pool = "".join(ch for ch in pool if ch.isalnum()) or (string.ascii_letters + string.digits)
        punct_pool = "".join(ch for ch in pool if not ch.isalnum()) or string.punctuation

        labels = ["alnum", "punct", "space", "newline"]
        weights = [
            max(0.0, float(cfg.unstructured_weight_alnum)),
            max(0.0, float(cfg.unstructured_weight_punct)),
            max(0.0, float(cfg.unstructured_weight_space)),
            max(0.0, float(cfg.unstructured_weight_newline)),
        ]

        # Optional tabs
        if cfg.unstructured_allow_tabs and float(cfg.unstructured_tab_weight) > 0:
            labels.append("tab")
            weights.append(max(0.0, float(cfg.unstructured_tab_weight)))

        if sum(weights) <= 0:
            # fallback: mostly alnum with some punctuation and spaces
            labels = ["alnum", "punct", "space", "newline"]
            weights = [0.62, 0.18, 0.16, 0.04]

        max_run = max(1, int(cfg.unstructured_max_run))

        out: List[str] = []
        n = 0
        while n < target:
            kind = weighted_choice(labels, weights)

            if kind == "alnum":
                run = random.randint(1, min(max_run, 32))
                chunk = "".join(random.choice(alnum_pool) for _ in range(run))
            elif kind == "punct":
                run = random.randint(1, min(max_run, 16))
                chunk = "".join(random.choice(punct_pool) for _ in range(run))
            elif kind == "space":
                run = random.randint(1, min(max_run, 12))
                chunk = " " * run
            elif kind == "newline":
                # bias toward single newlines but allow some doubles
                run = 1 if random.random() < 0.78 else 2
                chunk = "\n" * run
            else:  # tab
                run = 1 if random.random() < 0.85 else 2
                chunk = "\t" * run

            remaining = target - n
            if len(chunk) > remaining:
                chunk = chunk[:remaining]
            out.append(chunk)
            n += len(chunk)

        s = "".join(out)
        if not s.endswith("\n"):
            s += "\n"
        return s

    def generate_document(self) -> str:
        cfg = self.cfg
        if cfg.generator_mode == "unstructured":
            return self.generate_unstructured_document()

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




# ---------------- Telephone tree (cascading summaries + drift bands) ----------------
#
# This dataset method is designed to create "telephone game" style trees from meaningful
# seed texts, modeled around the WWW 2019 paper:
#   Horta Ribeiro, Gligorić, West — "Message Distortion in Information Cascades"
#
# The generator supports:
#   - cascading condition: each hop summarizes the previous hop (telephone effect)
#   - control condition: each hop summarizes the root directly (summary-only baseline)
#   - explicit acceptance bands for semantic similarity AND lexical overlap per hop
#   - JSONL export with full lineage metadata

_STOPWORDS = {
    "a","about","above","after","again","against","all","am","an","and","any","are","as","at",
    "be","because","been","before","being","below","between","both","but","by",
    "can","could",
    "did","do","does","doing","down","during",
    "each",
    "few","for","from","further",
    "had","has","have","having","he","her","here","hers","herself","him","himself","his","how",
    "i","if","in","into","is","it","its","itself",
    "just",
    "me","more","most","my","myself",
    "no","nor","not","now",
    "of","off","on","once","only","or","other","our","ours","ourselves","out","over","own",
    "same","she","should","so","some","such",
    "than","that","the","their","theirs","them","themselves","then","there","these","they","this","those","through","to","too",
    "under","until","up",
    "very",
    "was","we","were","what","when","where","which","while","who","whom","why","with","would",
    "you","your","yours","yourself","yourselves",
}

def _normalize_ws(text: str) -> str:
    # Collapse runs of whitespace but preserve paragraph breaks where possible.
    # For summaries, a single paragraph is usually fine.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Normalize internal whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _split_paragraphs(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return paras

def _split_sentences(text: str) -> List[str]:
    # Conservative sentence splitter, avoids external dependencies.
    # Keeps punctuation with the sentence.
    text = _normalize_ws(text)
    if not text:
        return []
    # Ensure newlines are treated as spaces for sentence splitting
    flat = re.sub(r"\s*\n\s*", " ", text)
    sents = re.split(r"(?<=[\.\!\?])\s+", flat)
    out = []
    for s in sents:
        s = s.strip()
        if not s:
            continue
        out.append(s)
    return out

def _word_tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())

def _content_tokens(text: str) -> List[str]:
    toks = _word_tokens(text)
    return [t for t in toks if t not in _STOPWORDS and len(t) > 1]

def _lexical_overlap_jaccard(parent_text: str, child_text: str) -> float:
    a = set(_content_tokens(parent_text))
    b = set(_content_tokens(child_text))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))

def _word_ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if n <= 0:
        return []
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def _ngram_copy_ratio(parent_text: str, child_text: str, n: int = 4) -> float:
    p = _word_tokens(parent_text)
    c = _word_tokens(child_text)
    c_ngrams = _word_ngrams(c, n)
    if not c_ngrams:
        return 0.0
    p_set = set(_word_ngrams(p, n))
    hits = sum(1 for g in c_ngrams if g in p_set)
    return hits / float(len(c_ngrams))

_CONNECTOR_REWRITES = [
    (r"\bHowever\b", "Nevertheless"),
    (r"\bTherefore\b", "So"),
    (r"\bIn addition\b", "Also"),
    (r"\bAdditionally\b", "Also"),
    (r"\bMoreover\b", "Also"),
    (r"\bThus\b", "So"),
    (r"\bConsequently\b", "As a result"),
    (r"\bFor example\b", "For instance"),
    (r"\bIn particular\b", "Specifically"),
]

def _light_rewrite_connectors(text: str, strength: float = 0.25) -> str:
    # Very mild rewrite to introduce some lexical drift while staying readable.
    # Applied probabilistically per pattern.
    out = text
    for pat, repl in _CONNECTOR_REWRITES:
        if random.random() < strength:
            out = re.sub(pat, repl, out)
    return out

class SemanticSimilarityScorer:
    """Computes a similarity score in [0,1] for two texts.

    Backends:
      - tfidf: TF-IDF cosine similarity (fast, lexical-ish but usable as a semantic proxy)
      - sbert: SentenceTransformer cosine similarity (requires sentence-transformers)
    """
    def __init__(self, backend: str = "tfidf"):
        self.backend = (backend or "tfidf").strip().lower()
        self._sbert_model = None

        if self.backend == "sbert":
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "SBERT backend requires the 'sentence-transformers' package. "
                    "Install it (pip install sentence-transformers) or switch to TF-IDF."
                ) from e
            # Default small model; user can edit code later if desired.
            self._sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

    def similarity(self, a: str, b: str) -> float:
        a = (a or "").strip()
        b = (b or "").strip()
        if not a or not b:
            return 0.0

        if self.backend == "sbert" and self._sbert_model is not None:
            import numpy as np  # local import
            va = self._sbert_model.encode([a], normalize_embeddings=True)
            vb = self._sbert_model.encode([b], normalize_embeddings=True)
            sim = float(np.dot(va[0], vb[0]))
            return max(0.0, min(1.0, sim))

        # TF-IDF backend
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except Exception:
            # Extremely small fallback: cosine on term frequency
            ca = Counter(_content_tokens(a))
            cb = Counter(_content_tokens(b))
            if not ca or not cb:
                return 0.0
            dot = sum(ca[t] * cb.get(t, 0) for t in ca.keys())
            na = sum(v * v for v in ca.values()) ** 0.5
            nb = sum(v * v for v in cb.values()) ** 0.5
            if na == 0 or nb == 0:
                return 0.0
            return max(0.0, min(1.0, dot / (na * nb)))

        vect = TfidfVectorizer(stop_words="english")
        X = vect.fit_transform([a, b])
        sim = float(cosine_similarity(X[0:1], X[1:2])[0][0])
        return max(0.0, min(1.0, sim))

class ExtractiveSummarizer:
    """Simple extractive sentence summarizer with mild randomness."""
    def __init__(self, jitter: float = 0.18, connector_rewrite_strength: float = 0.25):
        self.jitter = float(jitter)
        self.connector_rewrite_strength = float(connector_rewrite_strength)

    def summarize(self, text: str, target_chars: int, slack_chars: int) -> str:
        text = _normalize_ws(text)
        if not text:
            return ""

        sents = _split_sentences(text)
        if not sents:
            return text[:max(0, target_chars)].strip()

        # Compute content token frequencies across the full input
        freq = Counter(_content_tokens(text))
        if not freq:
            return self._fallback_lead(sents, target_chars, slack_chars)

        sent_scores: List[Tuple[float, int]] = []
        for i, s in enumerate(sents):
            toks = _content_tokens(s)
            if not toks:
                score = 0.0
            else:
                score = sum(freq.get(t, 0) for t in toks) / ((len(toks) + 1) ** 0.5)
            score *= (1.0 + random.uniform(-self.jitter, self.jitter))
            sent_scores.append((score, i))

        sent_scores.sort(reverse=True)

        selected: List[int] = []
        total = 0
        lo = max(0, int(target_chars) - int(slack_chars))
        hi = max(lo, int(target_chars) + int(slack_chars))

        for _score, idx in sent_scores:
            s = sents[idx].strip()
            if not s:
                continue
            add_len = len(s) + (1 if selected else 0)

            if total + add_len <= hi or total < lo:
                selected.append(idx)
                total += add_len

            if lo <= total <= hi and random.random() < 0.65:
                break

        if not selected:
            return self._fallback_lead(sents, target_chars, slack_chars)

        selected.sort()
        summary = " ".join(sents[i].strip() for i in selected if sents[i].strip())
        summary = _normalize_ws(summary)
        summary = _light_rewrite_connectors(summary, strength=self.connector_rewrite_strength)

        if len(summary) > hi and hi > 0:
            summary = summary[:hi].rsplit(" ", 1)[0].strip()

        if len(summary) < lo:
            for i in range(len(sents)):
                if i in selected:
                    continue
                s = sents[i].strip()
                if not s:
                    continue
                if len(summary) + 1 + len(s) > hi:
                    continue
                summary = (summary + " " + s).strip() if summary else s
                if len(summary) >= lo:
                    break

        return summary.strip()

    def _fallback_lead(self, sents: List[str], target_chars: int, slack_chars: int) -> str:
        lo = max(0, int(target_chars) - int(slack_chars))
        hi = max(lo, int(target_chars) + int(slack_chars))

        out: List[str] = []
        total = 0
        for s in sents:
            s = s.strip()
            if not s:
                continue
            add_len = len(s) + (1 if out else 0)
            if total + add_len <= hi or total < lo:
                out.append(s)
                total += add_len
            if lo <= total <= hi:
                break
        summary = " ".join(out).strip()
        if len(summary) > hi and hi > 0:
            summary = summary[:hi].rsplit(" ", 1)[0].strip()
        return summary

def _band_value(mode: str, start: float, end: float, hop: int, depth: int) -> float:
    if depth <= 1:
        return float(start)
    if (mode or "constant").strip().lower() != "linear":
        return float(start)
    t = (hop - 1) / float(depth - 1)
    return float(start + (end - start) * t)

class TelephoneCascadeBuilder:
    def __init__(self, cfg: TelephoneConfig, *, log_fn=None):
        self.cfg = cfg
        self.log_fn = log_fn or (lambda _m: None)
        self.scorer = SemanticSimilarityScorer(cfg.semantic_backend)
        self.summarizer = ExtractiveSummarizer()

        self._exact_seen: set[str] = set()
        self._dedupe_texts: List[str] = []
        self.rejected: Counter = Counter()

    def log(self, msg: str) -> None:
        try:
            self.log_fn(msg)
        except Exception:
            pass

    def load_roots(self) -> List[Tuple[str, str, Dict[str, str]]]:
        cfg = self.cfg
        mode = (cfg.seed_source_mode or "folder").strip().lower()
        path = Path((cfg.seed_path or "").strip()).expanduser()

        roots: List[Tuple[str, str, Dict[str, str]]] = []

        if not path.exists():
            raise ValueError("Seed path does not exist.")

        if mode == "folder":
            if not path.is_dir():
                raise ValueError("Seed source is set to 'folder' but the path is not a folder.")
            files = sorted([p for p in path.rglob("*.txt") if p.is_file()])
            if not files:
                raise ValueError("No .txt files found in the selected seed folder.")
            for fp in files:
                try:
                    raw = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                roots.extend(self._split_seed_text(raw, source=str(fp)))
        else:
            if not path.is_file():
                raise ValueError("Seed source is set to 'file' but the path is not a file.")
            raw = path.read_text(encoding="utf-8", errors="ignore")
            roots.extend(self._split_seed_text(raw, source=str(path)))

        cleaned: List[Tuple[str, str, Dict[str, str]]] = []
        for rid, txt, meta in roots:
            t = _normalize_ws(txt)
            if not t:
                continue
            cleaned.append((rid, t, meta))

        if cfg.shuffle_roots:
            random.shuffle(cleaned)

        if cfg.max_roots > 0:
            cleaned = cleaned[: int(cfg.max_roots)]

        if not cleaned:
            raise ValueError("No usable seed texts after splitting/filtering.")

        return cleaned

    def _split_seed_text(self, raw: str, *, source: str) -> List[Tuple[str, str, Dict[str, str]]]:
        cfg = self.cfg
        split_mode = (cfg.seed_split_mode or "whole_file").strip().lower()
        out: List[Tuple[str, str, Dict[str, str]]] = []

        if split_mode == "paragraphs":
            parts = _split_paragraphs(raw)
        elif split_mode == "fixed_chunks":
            n = max(200, int(cfg.fixed_chunk_chars))
            s = _normalize_ws(raw)
            parts = [s[i:i+n] for i in range(0, len(s), n)]
        else:
            parts = [raw]

        for i, part in enumerate(parts):
            rid = uuid.uuid4().hex
            meta = {"source": source, "split": split_mode, "split_index": str(i)}
            out.append((rid, part, meta))
        return out

    def build_schedule(self) -> Tuple[List[int], List[int]]:
        cfg = self.cfg
        d = max(1, int(cfg.depth))

        mdic_targets = [1000, 500, 250, 125, 64]
        mdic_slacks = [100, 50, 25, 13, 9]

        targets: List[int] = [0] * (d + 1)
        slacks: List[int] = [0] * (d + 1)

        mode = (cfg.length_schedule_mode or "mdic").strip().lower()
        if mode == "mdic":
            for hop in range(1, d + 1):
                if hop <= len(mdic_targets):
                    t = mdic_targets[hop - 1]
                else:
                    t = max(int(round(targets[hop - 1] * 0.5)), int(cfg.min_target_len))
                targets[hop] = max(int(cfg.min_target_len), int(t))
        elif mode == "geometric":
            t1 = max(int(cfg.min_target_len), int(cfg.geometric_first_target))
            ratio = float(cfg.geometric_ratio)
            ratio = max(0.05, min(0.95, ratio))
            for hop in range(1, d + 1):
                t = int(round(t1 * (ratio ** (hop - 1))))
                targets[hop] = max(int(cfg.min_target_len), int(t))
        else:
            raw = (cfg.custom_targets_csv or "").strip()
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            vals: List[int] = []
            for p in parts:
                try:
                    vals.append(int(p))
                except Exception:
                    pass
            if not vals:
                vals = mdic_targets[:]
            for hop in range(1, d + 1):
                t = vals[hop - 1] if hop - 1 < len(vals) else vals[-1]
                targets[hop] = max(int(cfg.min_target_len), int(t))

        slack_mode = (cfg.slack_mode or "mdic").strip().lower()
        if slack_mode == "mdic":
            for hop in range(1, d + 1):
                if hop <= len(mdic_slacks):
                    s = mdic_slacks[hop - 1]
                else:
                    s = max(5, int(round(targets[hop] * 0.08)))
                slacks[hop] = int(s)
        elif slack_mode == "percent":
            pct = float(cfg.slack_percent)
            pct = max(0.0, min(0.5, pct))
            for hop in range(1, d + 1):
                slacks[hop] = max(1, int(round(targets[hop] * pct)))
        else:
            s = max(0, int(cfg.slack_fixed))
            for hop in range(1, d + 1):
                slacks[hop] = s

        return targets, slacks

    def _accept_bands_for_hop(self, hop: int) -> Tuple[float, float, float, float]:
        cfg = self.cfg
        d = max(1, int(cfg.depth))
        mode = (cfg.band_schedule_mode or "constant").strip().lower()

        s_min = _band_value(mode, cfg.s_min_start, cfg.s_min_end, hop, d)
        s_max = _band_value(mode, cfg.s_max_start, cfg.s_max_end, hop, d)
        l_min = _band_value(mode, cfg.l_min_start, cfg.l_min_end, hop, d)
        l_max = _band_value(mode, cfg.l_max_start, cfg.l_max_end, hop, d)

        s_min = max(0.0, min(1.0, float(s_min)))
        s_max = max(0.0, min(1.0, float(s_max)))
        if s_min > s_max:
            s_min, s_max = s_max, s_min

        l_min = max(0.0, min(1.0, float(l_min)))
        l_max = max(0.0, min(1.0, float(l_max)))
        if l_min > l_max:
            l_min, l_max = l_max, l_min

        return s_min, s_max, l_min, l_max

    def _dedupe_ok(self, candidate: str) -> Tuple[bool, float]:
        cand_norm = _normalize_ws(candidate).lower()
        if not cand_norm:
            return False, 0.0
        if cand_norm in self._exact_seen:
            return False, 100.0

        threshold = float(self.cfg.dedupe_threshold)
        threshold = max(0.0, min(100.0, threshold))

        if threshold >= 100.0 or not self._dedupe_texts:
            return True, 0.0

        try:
            from rapidfuzz import fuzz, process  # type: ignore
        except Exception:
            return True, 0.0

        window = 2000
        hay = self._dedupe_texts[-window:]
        match = process.extractOne(cand_norm, hay, scorer=fuzz.ratio)
        best = float(match[1]) if match else 0.0
        if best >= threshold:
            return False, best
        return True, best

    def _register_text(self, text: str) -> None:
        norm = _normalize_ws(text).lower()
        self._exact_seen.add(norm)
        self._dedupe_texts.append(norm)

    def build(
        self,
        out_dir: Path,
        *,
        output_prefix: str,
        output_suffix: str,
        start_index: int,
        zero_pad_width: int,
        extension: str,
        overwrite: bool,
        export_settings_json: bool,
        settings_filename: str,
        include_file_list: bool,
    ) -> Dict[str, object]:
        cfg = self.cfg
        out_dir.mkdir(parents=True, exist_ok=True)

        jsonl_path: Optional[Path] = None
        if cfg.export_jsonl:
            jsonl_name = (cfg.jsonl_filename or "").strip()
            if not jsonl_name:
                jsonl_name = f"telephone_tree_{date_val}.jsonl"
            jsonl_path = out_dir / jsonl_name
            if not jsonl_path.name.lower().endswith(".jsonl"):
                jsonl_path = jsonl_path.with_suffix(".jsonl")

            if jsonl_path.exists() and not overwrite:
                jsonl_path = self._next_available_path(jsonl_path)

        targets, slacks = self.build_schedule()
        roots = self.load_roots()

        self.log(f"Telephone tree mode: roots={len(roots)} depth={cfg.depth} k={cfg.branching_factor} cap={cfg.max_samples_total}")
        if jsonl_path is not None:
            self.log(f"JSONL output: {jsonl_path.name}")
        else:
            self.log("JSONL export disabled; writing TXT nodes only.")

        jsonl_handle = jsonl_path.open("w", encoding="utf-8") if jsonl_path is not None else open(os.devnull, "w", encoding="utf-8")
        with jsonl_handle as f_jsonl:
            # Roots
            for root_id, root_text, meta in roots:
                if total_written >= int(cfg.max_samples_total):
                    break
                rec = {
                    "sample_id": uuid.uuid4().hex,
                    "root_id": root_id,
                    "parent_id": None,
                    "condition": "root",
                    "hop": 0,
                    "target_chars": None,
                    "slack_chars": None,
                    "text": root_text,
                    "metrics": {
                        "char_len": len(root_text),
                        "semantic_sim_parent": None,
                        "lexical_overlap_parent": None,
                        "ngram_copy_ratio": None,
                        "dedupe_score_max": None,
                    },
                    "source": meta,
                    "generation": {"backend": "seed"},
                }
                self._register_text(root_text)
                _emit(rec, root_text)

            # Control
            if cfg.include_control:
                self.log("Generating control condition (flat broadcast summaries)…")
                for root_id, root_text, meta in roots:
                    for hop in range(1, int(cfg.depth) + 1):
                        if total_written >= int(cfg.max_samples_total):
                            break
                        for _ in range(max(0, int(cfg.control_children_per_hop))):
                            if total_written >= int(cfg.max_samples_total):
                                break
                            target = int(targets[hop])
                            slack = int(slacks[hop])
                            child = self._generate_child_with_retries(
                                parent_text=root_text,
                                hop=hop,
                                target_chars=target,
                                slack_chars=slack,
                            )
                            if child is None:
                                continue

                            ok, best_dedupe = self._dedupe_ok(child)
                            if not ok:
                                self.rejected["dedupe(control)"] += 1
                                continue

                            sim = self.scorer.similarity(root_text, child)
                            lex = _lexical_overlap_jaccard(root_text, child)
                            copyr = _ngram_copy_ratio(root_text, child, n=4)

                            s_min, s_max, l_min, l_max = self._accept_bands_for_hop(hop)
                            if not (s_min <= sim <= s_max):
                                self.rejected["semantic_band(control)"] += 1
                                continue
                            if not (l_min <= lex <= l_max):
                                self.rejected["lexical_band(control)"] += 1
                                continue
                            if copyr > float(cfg.max_ngram_copy_ratio):
                                self.rejected["copy_ratio(control)"] += 1
                                continue

                            rec = {
                                "sample_id": uuid.uuid4().hex,
                                "root_id": root_id,
                                "parent_id": root_id,
                                "condition": "control",
                                "hop": hop,
                                "target_chars": target,
                                "slack_chars": slack,
                                "text": child,
                                "metrics": {
                                    "char_len": len(child),
                                    "semantic_sim_parent": sim,
                                    "lexical_overlap_parent": lex,
                                    "ngram_copy_ratio": copyr,
                                    "dedupe_score_max": best_dedupe,
                                },
                                "source": meta,
                                "generation": {"backend": "extractive_v1"},
                            }
                            self._register_text(child)
                            _emit(rec, child)

            # Cascade
            self.log("Generating cascading telephone tree…")
            frontier: List[Tuple[str, str, int, str]] = []
            for root_id, root_text, _meta in roots:
                frontier.append((root_id, root_id, 0, root_text))

            while frontier and total_written < int(cfg.max_samples_total):
                strat = (cfg.expansion_strategy or "bfs").strip().lower()
                if strat == "dfs":
                    root_id, parent_id, hop, parent_text = frontier.pop()
                elif strat == "random":
                    j = random.randrange(len(frontier))
                    root_id, parent_id, hop, parent_text = frontier.pop(j)
                else:
                    root_id, parent_id, hop, parent_text = frontier.pop(0)

                if hop >= int(cfg.depth):
                    continue

                next_hop = hop + 1
                target = int(targets[next_hop])
                slack = int(slacks[next_hop])

                for _child_i in range(max(0, int(cfg.branching_factor))):
                    if total_written >= int(cfg.max_samples_total):
                        break

                    child = self._generate_child_with_retries(
                        parent_text=parent_text,
                        hop=next_hop,
                        target_chars=target,
                        slack_chars=slack,
                    )
                    if child is None:
                        continue

                    ok, best_dedupe = self._dedupe_ok(child)
                    if not ok:
                        self.rejected["dedupe(cascade)"] += 1
                        continue

                    sim = self.scorer.similarity(parent_text, child)
                    lex = _lexical_overlap_jaccard(parent_text, child)
                    copyr = _ngram_copy_ratio(parent_text, child, n=4)

                    s_min, s_max, l_min, l_max = self._accept_bands_for_hop(next_hop)
                    if not (s_min <= sim <= s_max):
                        self.rejected["semantic_band(cascade)"] += 1
                        continue
                    if not (l_min <= lex <= l_max):
                        self.rejected["lexical_band(cascade)"] += 1
                        continue
                    if copyr > float(cfg.max_ngram_copy_ratio):
                        self.rejected["copy_ratio(cascade)"] += 1
                        continue

                    child_id = uuid.uuid4().hex
                    rec = {
                        "sample_id": child_id,
                        "root_id": root_id,
                        "parent_id": parent_id,
                        "condition": "cascade",
                        "hop": next_hop,
                        "target_chars": target,
                        "slack_chars": slack,
                        "text": child,
                        "metrics": {
                            "char_len": len(child),
                            "semantic_sim_parent": sim,
                            "lexical_overlap_parent": lex,
                            "ngram_copy_ratio": copyr,
                            "dedupe_score_max": best_dedupe,
                        },
                        "generation": {"backend": "extractive_v1"},
                    }

                    self._register_text(child)
                    _emit(rec, child)
                    frontier.append((root_id, child_id, next_hop, child))

        settings_path = out_dir / (settings_filename.strip() or "dataset_settings.json")
        if not settings_path.name.lower().endswith(".json"):
            settings_path = settings_path.with_suffix(".json")

        if export_settings_json:
            if settings_path.exists() and not overwrite:
                settings_path = self._next_available_path(settings_path)

            payload: Dict[str, object] = {
                "tool": "Noise Text Dataset Builder",
                "tool_version": getattr(App, "TOOL_VERSION", "unknown"),
                "created_at_local": _dt.datetime.now().isoformat(timespec="seconds"),
                "python": sys.version.replace("\n", " "),
                "dataset_method": "telephone",
                "telephone_config": asdict(cfg),
                "output": {
                    "out_dir": str(out_dir),
                    "jsonl": jsonl_path.name if jsonl_path is not None else None,
                    "export_txt_nodes": bool(cfg.export_txt_nodes),
                },
                "stats": {
                    "total_samples": total_written,
                    "rejected": dict(self.rejected),
                },
            }
            if include_file_list and created_txt_files:
                payload["generated_files"] = created_txt_files

            settings_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            self.log(f"Wrote settings JSON: {settings_path.name}")

        return {
            "jsonl": str(jsonl_path) if jsonl_path is not None else None,
            "settings_json": str(settings_path) if export_settings_json else None,
            "txt_files": created_txt_files,
            "total_samples": total_written,
            "rejected": dict(self.rejected),
        }

    def _generate_child_with_retries(self, *, parent_text: str, hop: int, target_chars: int, slack_chars: int) -> Optional[str]:
        cfg = self.cfg
        attempts = max(1, int(cfg.max_attempts_per_child))
        target = min(int(target_chars), max(int(cfg.min_target_len), len(parent_text)))
        slack = int(slack_chars)

        for _attempt in range(attempts):
            cand = self.summarizer.summarize(parent_text, target, slack)
            cand = _normalize_ws(cand)

            if not cand:
                self.rejected["empty"] += 1
                continue

            lo = max(0, target - slack)
            hi = max(lo, target + slack)
            if len(cand) < lo or len(cand) > hi:
                self.rejected["length"] += 1
                continue

            return cand

        self.rejected[f"max_attempts_h{hop}"] += 1
        return None

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
    TOOL_VERSION = "1.4"

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master.title("Noise Text Dataset Builder")
        self.master.geometry("1020x760")
        self.master.minsize(940, 680)

        # Separate configs per dataset method to keep behavior stable.
        self.cfg_noise = NoiseTextConfig()
        self.cfg_tel = TelephoneConfig()

        # Store grid args so we can show/hide frames reliably.
        self._grid_args: Dict[tk.Misc, Dict[str, object]] = {}

        self._build_ui()
        self._load_defaults_into_ui()
        self._on_dataset_method_change()
        self._update_preview()

    # ------------------------------ UI building ------------------------------

    def _remember_grid(self, widget: tk.Misc, **grid_kwargs) -> None:
        self._grid_args[widget] = dict(grid_kwargs)
        widget.grid(**grid_kwargs)

    def _grid_show(self, widget: tk.Misc) -> None:
        try:
            widget.grid(**self._grid_args.get(widget, {}))
        except Exception:
            try:
                widget.grid()
            except Exception:
                pass

    def _grid_hide(self, widget: tk.Misc) -> None:
        try:
            widget.grid_remove()
        except Exception:
            pass

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

        # ---------------- Dataset method ----------------
        self.dataset_method = tk.StringVar(value="noise")
        self.g_method = ttk.Labelframe(left, text="Dataset method", padding=10)
        self._remember_grid(self.g_method, row=0, column=0, sticky="ew", pady=(0, 10))
        self.g_method.grid_columnconfigure(0, weight=1)

        ttk.Label(
            self.g_method,
            text="Choose a dataset building method. 'Telephone tree' generates a branching cascade of summaries "
                 "from meaningful seed texts, with drift acceptance bands.",
            wraplength=420,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        mrow = ttk.Frame(self.g_method)
        ttk.Radiobutton(
            mrow, text="Noise generator (current)", variable=self.dataset_method, value="noise",
            command=self._on_dataset_method_change
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))
        ttk.Radiobutton(
            mrow, text="Telephone tree (cascading summaries)", variable=self.dataset_method, value="telephone",
            command=self._on_dataset_method_change
        ).grid(row=0, column=1, sticky="w")
        mrow.grid(row=1, column=0, sticky="w")

        # ---------------- Telephone groups (shown in telephone mode) ----------------

        self.g_tel_seed = ttk.Labelframe(left, text="Telephone: Seed texts", padding=10)
        self._remember_grid(self.g_tel_seed, row=1, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_seed.grid_columnconfigure(0, weight=1)

        self.tel_seed_source = tk.StringVar(value="folder")
        srow = ttk.Frame(self.g_tel_seed)
        ttk.Label(srow, text="Seed source").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Radiobutton(
            srow, text="Folder of .txt files", variable=self.tel_seed_source, value="folder",
            command=self._on_tel_seed_source_change
        ).grid(row=0, column=1, sticky="w", padx=(0, 10))
        ttk.Radiobutton(
            srow, text="Single .txt file", variable=self.tel_seed_source, value="file",
            command=self._on_tel_seed_source_change
        ).grid(row=0, column=2, sticky="w")
        srow.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.tel_seed_path = tk.StringVar(value="")
        prow = ttk.Frame(self.g_tel_seed)
        ttk.Label(prow, text="Seed path").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.e_tel_seed_path = ttk.Entry(prow, textvariable=self.tel_seed_path, width=38)
        self.e_tel_seed_path.grid(row=0, column=1, sticky="ew")
        self.btn_seed_browse = ttk.Button(prow, text="Browse…", command=self._browse_seed_path)
        self.btn_seed_browse.grid(row=0, column=2, sticky="w", padx=(8, 0))
        prow.grid_columnconfigure(1, weight=1)
        prow.grid(row=1, column=0, sticky="ew", pady=4)

        self.tel_seed_split = tk.StringVar(value="whole_file")
        splitrow = ttk.Frame(self.g_tel_seed)
        ttk.Label(splitrow, text="Split seeds").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_split = ttk.Combobox(
            splitrow, textvariable=self.tel_seed_split, width=18,
            values=["whole_file", "paragraphs", "fixed_chunks"], state="readonly"
        )
        self.cmb_tel_split.grid(row=0, column=1, sticky="w")
        self.cmb_tel_split.bind("<<ComboboxSelected>>", lambda _e: self._on_tel_seed_split_change())
        splitrow.grid(row=2, column=0, sticky="w", pady=4)

        self.e_tel_chunk_chars = LabeledEntry(self.g_tel_seed, "Chunk size (chars, fixed_chunks)", width=10)
        self.e_tel_chunk_chars.grid(row=3, column=0, sticky="w", pady=4)

        self.e_tel_max_roots = LabeledEntry(self.g_tel_seed, "Max roots to use", width=10)
        self.e_tel_max_roots.grid(row=4, column=0, sticky="w", pady=4)

        self.cb_tel_shuffle = tk.BooleanVar(value=False)
        self.w_tel_shuffle = ttk.Checkbutton(
            self.g_tel_seed, text="Shuffle roots (random subset order)", variable=self.cb_tel_shuffle,
            command=self._update_preview
        )
        self.w_tel_shuffle.grid(row=5, column=0, sticky="w", pady=(6, 0))

        # Schedule group
        self.g_tel_schedule = ttk.Labelframe(left, text="Telephone: Cascade schedule (targets + slack)", padding=10)
        self._remember_grid(self.g_tel_schedule, row=2, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_schedule.grid_columnconfigure(0, weight=1)

        self.e_tel_depth = LabeledEntry(self.g_tel_schedule, "Hops / depth", width=10)
        self.e_tel_depth.grid(row=0, column=0, sticky="w", pady=4)

        self.tel_len_mode = tk.StringVar(value="mdic")
        lrow = ttk.Frame(self.g_tel_schedule)
        ttk.Label(lrow, text="Target length schedule").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_len_mode = ttk.Combobox(
            lrow, textvariable=self.tel_len_mode, width=16,
            values=["mdic", "geometric", "custom"], state="readonly"
        )
        self.cmb_tel_len_mode.grid(row=0, column=1, sticky="w")
        self.cmb_tel_len_mode.bind("<<ComboboxSelected>>", lambda _e: self._on_tel_schedule_change())
        lrow.grid(row=1, column=0, sticky="w", pady=(6, 2))

        self.lbl_tel_mdic = ttk.Label(
            self.g_tel_schedule,
            text="MDIC preset (hop targets / slack): 1000±100, 500±50, 250±25, 125±13, 64±9",
            wraplength=420,
        )
        self.lbl_tel_mdic.grid(row=2, column=0, sticky="w", pady=(2, 6))

        self.e_tel_geo_first = LabeledEntry(self.g_tel_schedule, "Geometric: hop-1 target chars", width=10)
        self.e_tel_geo_ratio = LabeledEntry(self.g_tel_schedule, "Geometric: ratio (0.05..0.95)", width=10)
        self.e_tel_custom_targets = LabeledEntry(self.g_tel_schedule, "Custom targets CSV (per hop)", width=30)

        self.e_tel_geo_first.grid(row=3, column=0, sticky="w", pady=4)
        self.e_tel_geo_ratio.grid(row=4, column=0, sticky="w", pady=4)
        self.e_tel_custom_targets.grid(row=5, column=0, sticky="w", pady=4)

        self.tel_slack_mode = tk.StringVar(value="mdic")
        srow2 = ttk.Frame(self.g_tel_schedule)
        ttk.Label(srow2, text="Slack mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_slack_mode = ttk.Combobox(
            srow2, textvariable=self.tel_slack_mode, width=16,
            values=["mdic", "percent", "fixed"], state="readonly"
        )
        self.cmb_tel_slack_mode.grid(row=0, column=1, sticky="w")
        self.cmb_tel_slack_mode.bind("<<ComboboxSelected>>", lambda _e: self._on_tel_schedule_change())
        srow2.grid(row=6, column=0, sticky="w", pady=(10, 2))

        self.e_tel_slack_pct = LabeledEntry(self.g_tel_schedule, "Slack percent (0..0.5)", width=10)
        self.e_tel_slack_fixed = LabeledEntry(self.g_tel_schedule, "Slack fixed ± chars", width=10)
        self.e_tel_min_target = LabeledEntry(self.g_tel_schedule, "Minimum target length (chars)", width=10)

        self.e_tel_slack_pct.grid(row=7, column=0, sticky="w", pady=4)
        self.e_tel_slack_fixed.grid(row=8, column=0, sticky="w", pady=4)
        self.e_tel_min_target.grid(row=9, column=0, sticky="w", pady=4)

        # Branching group
        self.g_tel_branch = ttk.Labelframe(left, text="Telephone: Branching + dataset size", padding=10)
        self._remember_grid(self.g_tel_branch, row=3, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_branch.grid_columnconfigure(0, weight=1)

        self.e_tel_branch_k = LabeledEntry(self.g_tel_branch, "Cascade children per node (k)", width=10)
        self.e_tel_branch_k.grid(row=0, column=0, sticky="w", pady=4)

        self.cb_tel_control = tk.BooleanVar(value=True)
        self.w_tel_control = ttk.Checkbutton(
            self.g_tel_branch, text="Include control condition (summarize root directly each hop)",
            variable=self.cb_tel_control, command=self._update_preview
        )
        self.w_tel_control.grid(row=1, column=0, sticky="w", pady=(6, 4))

        self.e_tel_control_k = LabeledEntry(self.g_tel_branch, "Control children per hop", width=10)
        self.e_tel_control_k.grid(row=2, column=0, sticky="w", pady=4)

        self.e_tel_max_samples = LabeledEntry(self.g_tel_branch, "Max total samples (cap)", width=10)
        self.e_tel_max_samples.grid(row=3, column=0, sticky="w", pady=4)

        self.tel_expand = tk.StringVar(value="bfs")
        erow = ttk.Frame(self.g_tel_branch)
        ttk.Label(erow, text="Expansion strategy").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_expand = ttk.Combobox(
            erow, textvariable=self.tel_expand, width=10,
            values=["bfs", "dfs", "random"], state="readonly"
        )
        self.cmb_tel_expand.grid(row=0, column=1, sticky="w")
        erow.grid(row=4, column=0, sticky="w", pady=(10, 0))

        # Drift bands group
        self.g_tel_bands = ttk.Labelframe(left, text="Telephone: Drift acceptance bands", padding=10)
        self._remember_grid(self.g_tel_bands, row=4, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_bands.grid_columnconfigure(0, weight=1)

        self.tel_band_schedule = tk.StringVar(value="constant")
        brow = ttk.Frame(self.g_tel_bands)
        ttk.Label(brow, text="Band schedule").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_band_schedule = ttk.Combobox(
            brow, textvariable=self.tel_band_schedule, width=12,
            values=["constant", "linear"], state="readonly"
        )
        self.cmb_tel_band_schedule.grid(row=0, column=1, sticky="w")
        self.cmb_tel_band_schedule.bind("<<ComboboxSelected>>", lambda _e: self._on_tel_bands_change())
        brow.grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Label(self.g_tel_bands, text="Semantic similarity band (cosine):").grid(row=1, column=0, sticky="w", pady=(4, 2))
        self.e_tel_smin_start = LabeledEntry(self.g_tel_bands, "S min (start)", width=10)
        self.e_tel_smax_start = LabeledEntry(self.g_tel_bands, "S max (start)", width=10)
        self.e_tel_smin_end = LabeledEntry(self.g_tel_bands, "S min (end)", width=10)
        self.e_tel_smax_end = LabeledEntry(self.g_tel_bands, "S max (end)", width=10)
        self.e_tel_smin_start.grid(row=2, column=0, sticky="w", pady=2)
        self.e_tel_smax_start.grid(row=3, column=0, sticky="w", pady=2)
        self.e_tel_smin_end.grid(row=4, column=0, sticky="w", pady=2)
        self.e_tel_smax_end.grid(row=5, column=0, sticky="w", pady=2)

        ttk.Label(self.g_tel_bands, text="Lexical overlap band (Jaccard of content tokens):").grid(row=6, column=0, sticky="w", pady=(8, 2))
        self.e_tel_lmin_start = LabeledEntry(self.g_tel_bands, "L min (start)", width=10)
        self.e_tel_lmax_start = LabeledEntry(self.g_tel_bands, "L max (start)", width=10)
        self.e_tel_lmin_end = LabeledEntry(self.g_tel_bands, "L min (end)", width=10)
        self.e_tel_lmax_end = LabeledEntry(self.g_tel_bands, "L max (end)", width=10)
        self.e_tel_lmin_start.grid(row=7, column=0, sticky="w", pady=2)
        self.e_tel_lmax_start.grid(row=8, column=0, sticky="w", pady=2)
        self.e_tel_lmin_end.grid(row=9, column=0, sticky="w", pady=2)
        self.e_tel_lmax_end.grid(row=10, column=0, sticky="w", pady=2)

        self.e_tel_attempts = LabeledEntry(self.g_tel_bands, "Max attempts per child", width=10)
        self.e_tel_copyratio = LabeledEntry(self.g_tel_bands, "Max 4-gram copy ratio (0..1)", width=10)
        self.e_tel_attempts.grid(row=11, column=0, sticky="w", pady=(10, 2))
        self.e_tel_copyratio.grid(row=12, column=0, sticky="w", pady=2)

        # Scoring/dedupe group
        self.g_tel_scoring = ttk.Labelframe(left, text="Telephone: Scoring + dedupe", padding=10)
        self._remember_grid(self.g_tel_scoring, row=5, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_scoring.grid_columnconfigure(0, weight=1)

        self.tel_sem_backend = tk.StringVar(value="tfidf")
        sbrow = ttk.Frame(self.g_tel_scoring)
        ttk.Label(sbrow, text="Semantic similarity backend").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_tel_sem_backend = ttk.Combobox(
            sbrow, textvariable=self.tel_sem_backend, width=10,
            values=["tfidf", "sbert"], state="readonly"
        )
        self.cmb_tel_sem_backend.grid(row=0, column=1, sticky="w")
        sbrow.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.e_tel_dedupe = LabeledEntry(self.g_tel_scoring, "Dedupe threshold (RapidFuzz ratio 0..100)", width=10)
        self.e_tel_dedupe.grid(row=1, column=0, sticky="w", pady=4)

        # Export + presets group
        self.g_tel_export = ttk.Labelframe(left, text="Telephone: Export + presets", padding=10)
        self._remember_grid(self.g_tel_export, row=6, column=0, sticky="ew", pady=(0, 10))
        self.g_tel_export.grid_columnconfigure(0, weight=1)

        self.cb_tel_jsonl = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.g_tel_export, text="Export JSONL dataset", variable=self.cb_tel_jsonl,
            command=self._update_preview
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.e_tel_jsonl_name = LabeledEntry(self.g_tel_export, "JSONL filename", width=28)
        self.e_tel_jsonl_name.grid(row=1, column=0, sticky="w", pady=4)

        self.cb_tel_txt = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.g_tel_export, text="Also export .txt files for each node", variable=self.cb_tel_txt,
            command=self._update_preview
        ).grid(row=2, column=0, sticky="w", pady=(6, 4))

        pres_row = ttk.Frame(self.g_tel_export)
        ttk.Label(pres_row, text="Preset").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.tel_preset = tk.StringVar(value="MDIC (paper-style)")
        self.cmb_tel_preset = ttk.Combobox(
            pres_row, textvariable=self.tel_preset, width=22,
            values=["MDIC (paper-style)", "Lexicon-agnostic stress", "Readable paragraphs"],
            state="readonly"
        )
        self.cmb_tel_preset.grid(row=0, column=1, sticky="w")
        ttk.Button(pres_row, text="Apply preset", command=self._apply_tel_preset).grid(row=0, column=2, padx=(8, 0))
        pres_row.grid(row=3, column=0, sticky="w", pady=(12, 0))

        # ---------------- Noise groups (shown in noise mode) ----------------

        self.g_dataset = ttk.Labelframe(left, text="Dataset size & structure", padding=10)
        self._remember_grid(self.g_dataset, row=7, column=0, sticky="ew", pady=(0, 10))
        self.g_dataset.grid_columnconfigure(0, weight=1)

        self.e_num_files = LabeledEntry(self.g_dataset, "Number of files", width=10)
        self.r_sentences = RangeRow(self.g_dataset, "Sentences per file", width=8)
        self.r_words = RangeRow(self.g_dataset, "Words per sentence", width=8)

        self.e_num_files.grid(row=0, column=0, sticky="w", pady=4)
        self.r_sentences.grid(row=1, column=0, sticky="w", pady=4)
        self.r_words.grid(row=2, column=0, sticky="w", pady=4)

        self.g_wordlen = ttk.Labelframe(left, text="Word length distribution", padding=10)
        self._remember_grid(self.g_wordlen, row=8, column=0, sticky="ew", pady=(0, 10))
        self.g_wordlen.grid_columnconfigure(0, weight=1)

        self.e_word_mean = LabeledEntry(self.g_wordlen, "Average letters per word", width=10)
        self.e_word_sd = LabeledEntry(self.g_wordlen, "Word length stdev", width=10)
        self.r_wordlen_bounds = RangeRow(self.g_wordlen, "Word length bounds", width=8)

        self.e_word_mean.grid(row=0, column=0, sticky="w", pady=4)
        self.e_word_sd.grid(row=1, column=0, sticky="w", pady=4)
        self.r_wordlen_bounds.grid(row=2, column=0, sticky="w", pady=4)

        self.g_gen = ttk.Labelframe(left, text="Base word generator", padding=10)
        self._remember_grid(self.g_gen, row=9, column=0, sticky="ew", pady=(0, 10))
        self.g_gen.grid_columnconfigure(0, weight=1)

        self.gen_mode = tk.StringVar(value="syllable")
        modes = ttk.Frame(self.g_gen)
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
        ttk.Radiobutton(
            modes, text="Dictionary words (real English words)", variable=self.gen_mode, value="dictionary",
            command=self._on_mode_change
        ).grid(row=3, column=1, sticky="w")
        ttk.Radiobutton(
            modes, text="Unstructured (random chars/punct/spaces)", variable=self.gen_mode, value="unstructured",
            command=self._on_mode_change
        ).grid(row=4, column=1, sticky="w")
        modes.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.cb_allow_double = tk.BooleanVar(value=True)
        self.w_allow_double = ttk.Checkbutton(
            self.g_gen, text="Allow doubled letters (e.g., 'tt')", variable=self.cb_allow_double,
            command=self._update_preview
        )
        self.w_allow_double.grid(row=1, column=0, sticky="w", pady=4)

        self.r_syllables = RangeRow(self.g_gen, "Syllables per word", width=8)
        self.r_syllables.grid(row=2, column=0, sticky="w", pady=4)

        self.e_alphabet = LabeledEntry(self.g_gen, "Alphabet (uniform mode)", width=30)
        self.e_alphabet.grid(row=3, column=0, sticky="w", pady=4)

        self.g_unstruct = ttk.Labelframe(left, text="Unstructured noise mode", padding=10)
        self._remember_grid(self.g_unstruct, row=10, column=0, sticky="ew", pady=(0, 10))
        self.g_unstruct.grid_columnconfigure(0, weight=1)

        ttk.Label(
            self.g_unstruct,
            text="Generates unpredictable streams of characters/punctuation/spaces (ignores sentence/word settings).",
            wraplength=420,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.r_un_chars = RangeRow(self.g_unstruct, "Characters per file", width=8)
        self.r_un_chars.grid(row=1, column=0, sticky="w", pady=4)

        self.e_un_pool = LabeledEntry(self.g_unstruct, "Char pool (non-whitespace)", width=36)
        self.e_un_pool.grid(row=2, column=0, sticky="w", pady=4)

        wrow = ttk.Frame(self.g_unstruct)
        ttk.Label(wrow, text="Category weights").grid(row=0, column=0, sticky="w", columnspan=8, pady=(0, 4))
        self.e_un_w_alnum = LabeledEntry(wrow, "alnum", width=8)
        self.e_un_w_punct = LabeledEntry(wrow, "punct", width=8)
        self.e_un_w_space = LabeledEntry(wrow, "space", width=8)
        self.e_un_w_newline = LabeledEntry(wrow, "newline", width=8)
        self.e_un_w_alnum.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.e_un_w_punct.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.e_un_w_space.grid(row=1, column=2, sticky="w", padx=(0, 10))
        self.e_un_w_newline.grid(row=1, column=3, sticky="w")
        wrow.grid(row=3, column=0, sticky="w", pady=6)

        self.e_un_max_run = LabeledEntry(self.g_unstruct, "Max run length", width=10)
        self.e_un_max_run.grid(row=4, column=0, sticky="w", pady=4)

        self.cb_un_tabs = tk.BooleanVar(value=False)
        self.w_un_tabs = ttk.Checkbutton(
            self.g_unstruct, text="Allow TAB characters (\\t) as whitespace", variable=self.cb_un_tabs,
            command=self._on_mode_change
        )
        self.w_un_tabs.grid(row=5, column=0, sticky="w", pady=(6, 4))

        self.e_un_tab_weight = LabeledEntry(self.g_unstruct, "Tab weight (if enabled)", width=10)
        self.e_un_tab_weight.grid(row=6, column=0, sticky="w", pady=4)

        self.g_zipf = ttk.Labelframe(left, text="Zipf-like reuse, POS lexicons & entities", padding=10)
        self._remember_grid(self.g_zipf, row=11, column=0, sticky="ew", pady=(0, 10))
        self.g_zipf.grid_columnconfigure(0, weight=1)

        self.cb_zipf = tk.BooleanVar(value=True)
        self.w_zipf_enable = ttk.Checkbutton(
            self.g_zipf, text="Enable Zipf-like word reuse (more natural repetition)",
            variable=self.cb_zipf, command=self._on_zipf_toggle
        )
        self.w_zipf_enable.grid(row=0, column=0, sticky="w", pady=4)

        self.e_zipf_exp = LabeledEntry(self.g_zipf, "Zipf exponent (≈ 1.0)", width=10)
        self.e_zipf_exp.grid(row=1, column=0, sticky="w", pady=4)

        self.cb_pos_suffix = tk.BooleanVar(value=True)
        self.w_pos_suffix = ttk.Checkbutton(
            self.g_zipf, text="Add POS-like suffixes (e.g., -ly, -ing) in lexicons",
            variable=self.cb_pos_suffix, command=self._update_preview
        )
        self.w_pos_suffix.grid(row=2, column=0, sticky="w", pady=4)

        self.e_func_vocab = LabeledEntry(self.g_zipf, "Function vocab size (DET/PREP/CONJ/PRON)", width=10)
        self.e_cont_vocab = LabeledEntry(self.g_zipf, "Content vocab size (NOUN/VERB/ADJ/ADV)", width=10)
        self.e_ent_vocab = LabeledEntry(self.g_zipf, "Entity phrase vocab size", width=10)
        self.e_func_vocab.grid(row=3, column=0, sticky="w", pady=4)
        self.e_cont_vocab.grid(row=4, column=0, sticky="w", pady=4)
        self.e_ent_vocab.grid(row=5, column=0, sticky="w", pady=4)

        self.r_ent_len = RangeRow(self.g_zipf, "Entity words per phrase", width=8)
        self.r_ent_len.grid(row=6, column=0, sticky="w", pady=4)

        self.e_ent_start_rate = LabeledEntry(self.g_zipf, "Entity at sentence start rate (0..1)", width=10)
        self.e_ent_noun_rate = LabeledEntry(self.g_zipf, "Replace NOUN with entity rate (0..1)", width=10)
        self.e_ent_start_rate.grid(row=7, column=0, sticky="w", pady=4)
        self.e_ent_noun_rate.grid(row=8, column=0, sticky="w", pady=4)

        self.g_style = ttk.Labelframe(left, text="Sentence styling", padding=10)
        self._remember_grid(self.g_style, row=12, column=0, sticky="ew", pady=(0, 10))
        self.g_style.grid_columnconfigure(0, weight=1)

        self.cb_cap_start = tk.BooleanVar(value=True)
        self.w_cap_start = ttk.Checkbutton(
            self.g_style, text="Capitalize first word of each sentence", variable=self.cb_cap_start,
            command=self._update_preview
        )
        self.w_cap_start.grid(row=0, column=0, sticky="w", pady=4)

        self.e_proper_rate = LabeledEntry(self.g_style, "Extra Title-Case word rate (0..1)", width=10)
        self.e_caps_rate = LabeledEntry(self.g_style, "ALL-CAPS word rate (0..1)", width=10)
        self.e_proper_rate.grid(row=1, column=0, sticky="w", pady=4)
        self.e_caps_rate.grid(row=2, column=0, sticky="w", pady=4)

        self.g_punct = ttk.Labelframe(left, text="Punctuation & paragraphs", padding=10)
        self._remember_grid(self.g_punct, row=13, column=0, sticky="ew", pady=(0, 10))
        self.g_punct.grid_columnconfigure(0, weight=1)

        self.e_comma_rate = LabeledEntry(self.g_punct, "Comma insertion rate (0..1)", width=10)
        self.e_max_commas = LabeledEntry(self.g_punct, "Max commas per sentence", width=10)
        self.e_comma_rate.grid(row=0, column=0, sticky="w", pady=4)
        self.e_max_commas.grid(row=1, column=0, sticky="w", pady=4)

        g_end = ttk.Frame(self.g_punct)
        ttk.Label(g_end, text="Sentence end punctuation weights").grid(row=0, column=0, sticky="w", columnspan=6, pady=(0, 4))
        self.e_w_period = LabeledEntry(g_end, "'.' weight", width=8)
        self.e_w_q = LabeledEntry(g_end, "'?' weight", width=8)
        self.e_w_ex = LabeledEntry(g_end, "'!' weight", width=8)
        self.e_w_period.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.e_w_q.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.e_w_ex.grid(row=1, column=2, sticky="w")
        g_end.grid(row=2, column=0, sticky="w", pady=6)

        self.cb_paras = tk.BooleanVar(value=True)
        self.w_paras = ttk.Checkbutton(
            self.g_punct, text="Enable paragraph breaks", variable=self.cb_paras,
            command=self._update_preview
        )
        self.w_paras.grid(row=3, column=0, sticky="w", pady=4)
        self.r_para_every = RangeRow(self.g_punct, "Paragraph break every N sentences", width=8)
        self.r_para_every.grid(row=4, column=0, sticky="w", pady=4)

        # ---------------- Output settings (shared) ----------------
        self.g_out = ttk.Labelframe(left, text="Output settings", padding=10)
        self._remember_grid(self.g_out, row=14, column=0, sticky="ew", pady=(0, 10))
        self.g_out.grid_columnconfigure(0, weight=1)

        self.out_dir = tk.StringVar(value="C:/temp")
        row_dir = ttk.Frame(self.g_out)
        ttk.Label(row_dir, text="Save folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.e_dir = ttk.Entry(row_dir, textvariable=self.out_dir, width=38)
        self.e_dir.grid(row=0, column=1, sticky="ew")
        ttk.Button(row_dir, text="Browse…", command=self._browse_dir).grid(row=0, column=2, sticky="w", padx=(8, 0))
        row_dir.grid_columnconfigure(1, weight=1)
        row_dir.grid(row=0, column=0, sticky="ew", pady=4)

        self.e_prefix = LabeledEntry(self.g_out, "Filename prefix", width=20)
        self.e_suffix = LabeledEntry(self.g_out, "Filename suffix", width=20)
        self.e_start_index = LabeledEntry(self.g_out, "Start number", width=10)
        self.e_pad = LabeledEntry(self.g_out, "Zero-pad width", width=10)
        self.e_ext = LabeledEntry(self.g_out, "Extension", width=10)
        self.e_seed = LabeledEntry(self.g_out, "Seed (optional)", width=20)

        self.e_prefix.grid(row=1, column=0, sticky="w", pady=4)
        self.e_suffix.grid(row=2, column=0, sticky="w", pady=4)
        self.e_start_index.grid(row=3, column=0, sticky="w", pady=4)
        self.e_pad.grid(row=4, column=0, sticky="w", pady=4)
        self.e_ext.grid(row=5, column=0, sticky="w", pady=4)
        self.e_seed.grid(row=6, column=0, sticky="w", pady=4)

        self.cb_overwrite = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.g_out, text="Overwrite existing files", variable=self.cb_overwrite).grid(
            row=7, column=0, sticky="w", pady=(6, 4)
        )

        self.cb_export_json = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.g_out, text="Export JSON settings sidecar", variable=self.cb_export_json
        ).grid(row=8, column=0, sticky="w", pady=(8, 4))

        self.e_json_name = LabeledEntry(self.g_out, "Settings JSON filename", width=24)
        self.e_json_name.grid(row=9, column=0, sticky="w", pady=4)

        self.cb_json_filelist = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.g_out, text="Include generated file list in JSON", variable=self.cb_json_filelist
        ).grid(row=10, column=0, sticky="w", pady=4)

        self.cb_json_vocab = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.g_out, text="Include vocabularies in JSON (can be large)", variable=self.cb_json_vocab
        ).grid(row=11, column=0, sticky="w", pady=4)

        btns = ttk.Frame(left)
        ttk.Button(btns, text="Preview sample", command=self._update_preview).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Generate files", command=self._generate_files).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Reset defaults", command=self._reset_defaults).grid(row=0, column=2)
        self._remember_grid(btns, row=15, column=0, sticky="w", pady=(4, 0))

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
            self.e_dir,
            self.e_num_files.entry, self.r_sentences.min_entry, self.r_sentences.max_entry,
            self.r_words.min_entry, self.r_words.max_entry,
            self.e_word_mean.entry, self.e_word_sd.entry,
            self.r_wordlen_bounds.min_entry, self.r_wordlen_bounds.max_entry,
            self.r_syllables.min_entry, self.r_syllables.max_entry,
            self.e_alphabet.entry,

            self.r_un_chars.min_entry, self.r_un_chars.max_entry,
            self.e_un_pool.entry,
            self.e_un_w_alnum.entry, self.e_un_w_punct.entry, self.e_un_w_space.entry, self.e_un_w_newline.entry,
            self.e_un_max_run.entry,
            self.e_un_tab_weight.entry,

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

            self.e_tel_seed_path,
            self.e_tel_chunk_chars.entry,
            self.e_tel_max_roots.entry,
            self.e_tel_depth.entry,
            self.e_tel_geo_first.entry, self.e_tel_geo_ratio.entry,
            self.e_tel_custom_targets.entry,
            self.e_tel_slack_pct.entry, self.e_tel_slack_fixed.entry,
            self.e_tel_min_target.entry,
            self.e_tel_branch_k.entry, self.e_tel_control_k.entry,
            self.e_tel_max_samples.entry,
            self.e_tel_smin_start.entry, self.e_tel_smax_start.entry,
            self.e_tel_smin_end.entry, self.e_tel_smax_end.entry,
            self.e_tel_lmin_start.entry, self.e_tel_lmax_start.entry,
            self.e_tel_lmin_end.entry, self.e_tel_lmax_end.entry,
            self.e_tel_attempts.entry, self.e_tel_copyratio.entry,
            self.e_tel_dedupe.entry,
            self.e_tel_jsonl_name.entry,
        ]
        for widget in watched:
            try:
                widget.bind("<FocusOut>", lambda _e: self._update_preview())
            except Exception:
                pass

    # ------------------------------ UI actions ------------------------------

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg.rstrip() + "\n")
        self.log.see("end")

    def _browse_dir(self) -> None:
        p = filedialog.askdirectory(title="Choose output folder")
        if p:
            self.out_dir.set(p)
            self._update_preview()

    def _browse_seed_path(self) -> None:
        mode = (self.tel_seed_source.get() or "folder").strip().lower()
        if mode == "file":
            p = filedialog.askopenfilename(title="Choose seed .txt file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        else:
            p = filedialog.askdirectory(title="Choose seed folder (containing .txt files)")
        if p:
            self.tel_seed_path.set(p)
            self._update_preview()

    def _reset_defaults(self) -> None:
        self.cfg_noise = NoiseTextConfig()
        self.cfg_tel = TelephoneConfig()
        self._load_defaults_into_ui()
        self._on_dataset_method_change()
        self._update_preview()
        self._log("Reset to defaults.")

    def _load_defaults_into_ui(self) -> None:
        c = self.cfg_noise
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

        self.r_un_chars.set(c.unstructured_min_chars, c.unstructured_max_chars)
        self.e_un_pool.set(c.unstructured_pool)
        self.e_un_w_alnum.set(c.unstructured_weight_alnum)
        self.e_un_w_punct.set(c.unstructured_weight_punct)
        self.e_un_w_space.set(c.unstructured_weight_space)
        self.e_un_w_newline.set(c.unstructured_weight_newline)
        self.e_un_max_run.set(c.unstructured_max_run)
        self.cb_un_tabs.set(c.unstructured_allow_tabs)
        self.e_un_tab_weight.set(c.unstructured_tab_weight)

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

        t = self.cfg_tel
        self.tel_seed_source.set(t.seed_source_mode)
        self.tel_seed_path.set(t.seed_path)
        self.tel_seed_split.set(t.seed_split_mode)
        self.e_tel_chunk_chars.set(t.fixed_chunk_chars)
        self.e_tel_max_roots.set(t.max_roots)
        self.cb_tel_shuffle.set(t.shuffle_roots)

        self.e_tel_depth.set(t.depth)
        self.tel_len_mode.set(t.length_schedule_mode)
        self.e_tel_geo_first.set(t.geometric_first_target)
        self.e_tel_geo_ratio.set(t.geometric_ratio)
        self.e_tel_custom_targets.set(t.custom_targets_csv)

        self.tel_slack_mode.set(t.slack_mode)
        self.e_tel_slack_pct.set(t.slack_percent)
        self.e_tel_slack_fixed.set(t.slack_fixed)
        self.e_tel_min_target.set(t.min_target_len)

        self.e_tel_branch_k.set(t.branching_factor)
        self.cb_tel_control.set(t.include_control)
        self.e_tel_control_k.set(t.control_children_per_hop)
        self.e_tel_max_samples.set(t.max_samples_total)
        self.tel_expand.set(t.expansion_strategy)

        self.tel_band_schedule.set(t.band_schedule_mode)
        self.e_tel_smin_start.set(t.s_min_start)
        self.e_tel_smax_start.set(t.s_max_start)
        self.e_tel_smin_end.set(t.s_min_end)
        self.e_tel_smax_end.set(t.s_max_end)
        self.e_tel_lmin_start.set(t.l_min_start)
        self.e_tel_lmax_start.set(t.l_max_start)
        self.e_tel_lmin_end.set(t.l_min_end)
        self.e_tel_lmax_end.set(t.l_max_end)
        self.e_tel_attempts.set(t.max_attempts_per_child)
        self.e_tel_copyratio.set(t.max_ngram_copy_ratio)

        self.tel_sem_backend.set(t.semantic_backend)
        self.e_tel_dedupe.set(t.dedupe_threshold)

        self.cb_tel_jsonl.set(t.export_jsonl)
        self.e_tel_jsonl_name.set(t.jsonl_filename)
        self.cb_tel_txt.set(t.export_txt_nodes)

        self._on_mode_change()
        self._on_zipf_toggle()
        self._on_tel_seed_split_change()
        self._on_tel_schedule_change()
        self._on_tel_bands_change()
        self._on_tel_seed_source_change()

    # ----------------------- Dataset method switching -----------------------

    def _on_dataset_method_change(self) -> None:
        method = (self.dataset_method.get() or "noise").strip().lower()

        tel_frames = [self.g_tel_seed, self.g_tel_schedule, self.g_tel_branch, self.g_tel_bands, self.g_tel_scoring, self.g_tel_export]
        noise_frames = [self.g_dataset, self.g_wordlen, self.g_gen, self.g_unstruct, self.g_zipf, self.g_style, self.g_punct]

        if method == "telephone":
            for f in noise_frames:
                self._grid_hide(f)
            for f in tel_frames:
                self._grid_show(f)
        else:
            for f in tel_frames:
                self._grid_hide(f)
            for f in noise_frames:
                self._grid_show(f)

        self._update_preview()

    # ---------------- Telephone UI enable/disable ----------------

    def _on_tel_seed_source_change(self) -> None:
        mode = (self.tel_seed_source.get() or "folder").strip().lower()
        try:
            self.btn_seed_browse.configure(text="Browse file…" if mode == "file" else "Browse folder…")
        except Exception:
            pass

    def _on_tel_seed_split_change(self) -> None:
        split_mode = (self.tel_seed_split.get() or "whole_file").strip().lower()
        state = "normal" if split_mode == "fixed_chunks" else "disabled"
        try:
            self.e_tel_chunk_chars.entry.configure(state=state)
        except Exception:
            pass
        self._update_preview()

    def _on_tel_schedule_change(self) -> None:
        mode = (self.tel_len_mode.get() or "mdic").strip().lower()
        slack_mode = (self.tel_slack_mode.get() or "mdic").strip().lower()

        if mode == "geometric":
            self.e_tel_geo_first.entry.configure(state="normal")
            self.e_tel_geo_ratio.entry.configure(state="normal")
            self.e_tel_custom_targets.entry.configure(state="disabled")
        elif mode == "custom":
            self.e_tel_geo_first.entry.configure(state="disabled")
            self.e_tel_geo_ratio.entry.configure(state="disabled")
            self.e_tel_custom_targets.entry.configure(state="normal")
        else:
            self.e_tel_geo_first.entry.configure(state="disabled")
            self.e_tel_geo_ratio.entry.configure(state="disabled")
            self.e_tel_custom_targets.entry.configure(state="disabled")

        if slack_mode == "percent":
            self.e_tel_slack_pct.entry.configure(state="normal")
            self.e_tel_slack_fixed.entry.configure(state="disabled")
        elif slack_mode == "fixed":
            self.e_tel_slack_pct.entry.configure(state="disabled")
            self.e_tel_slack_fixed.entry.configure(state="normal")
        else:
            self.e_tel_slack_pct.entry.configure(state="disabled")
            self.e_tel_slack_fixed.entry.configure(state="disabled")

        self._update_preview()

    def _on_tel_bands_change(self) -> None:
        mode = (self.tel_band_schedule.get() or "constant").strip().lower()
        end_state = "normal" if mode == "linear" else "disabled"
        for w in [
            self.e_tel_smin_end.entry, self.e_tel_smax_end.entry,
            self.e_tel_lmin_end.entry, self.e_tel_lmax_end.entry,
        ]:
            try:
                w.configure(state=end_state)
            except Exception:
                pass
        self._update_preview()

    def _apply_tel_preset(self) -> None:
        p = (self.tel_preset.get() or "").strip()

        if p == "Lexicon-agnostic stress":
            self.e_tel_depth.set(6)
            self.tel_len_mode.set("geometric")
            self.e_tel_geo_first.set(1200)
            self.e_tel_geo_ratio.set(0.75)
            self.tel_slack_mode.set("percent")
            self.e_tel_slack_pct.set(0.06)
            self.e_tel_min_target.set(400)

            self.e_tel_branch_k.set(3)
            self.cb_tel_control.set(True)
            self.e_tel_control_k.set(1)
            self.e_tel_max_samples.set(10000)
            self.tel_expand.set("bfs")

            self.tel_band_schedule.set("linear")
            self.e_tel_smin_start.set(0.85)
            self.e_tel_smax_start.set(0.97)
            self.e_tel_smin_end.set(0.65)
            self.e_tel_smax_end.set(0.88)

            self.e_tel_lmin_start.set(0.35)
            self.e_tel_lmax_start.set(0.65)
            self.e_tel_lmin_end.set(0.05)
            self.e_tel_lmax_end.set(0.25)

            self.e_tel_attempts.set(40)
            self.e_tel_copyratio.set(0.20)
            self.tel_sem_backend.set("tfidf")
            self.e_tel_dedupe.set(97.0)

        elif p == "Readable paragraphs":
            self.e_tel_depth.set(5)
            self.tel_len_mode.set("geometric")
            self.e_tel_geo_first.set(1400)
            self.e_tel_geo_ratio.set(0.80)
            self.tel_slack_mode.set("percent")
            self.e_tel_slack_pct.set(0.05)
            self.e_tel_min_target.set(700)

            self.e_tel_branch_k.set(2)
            self.cb_tel_control.set(True)
            self.e_tel_control_k.set(1)
            self.e_tel_max_samples.set(5000)
            self.tel_expand.set("bfs")

            self.tel_band_schedule.set("constant")
            self.e_tel_smin_start.set(0.78)
            self.e_tel_smax_start.set(0.97)
            self.e_tel_smin_end.set(0.78)
            self.e_tel_smax_end.set(0.97)

            self.e_tel_lmin_start.set(0.20)
            self.e_tel_lmax_start.set(0.55)
            self.e_tel_lmin_end.set(0.20)
            self.e_tel_lmax_end.set(0.55)

            self.e_tel_attempts.set(30)
            self.e_tel_copyratio.set(0.20)
            self.tel_sem_backend.set("tfidf")
            self.e_tel_dedupe.set(96.0)

        else:
            self.e_tel_depth.set(5)
            self.tel_len_mode.set("mdic")
            self.tel_slack_mode.set("mdic")
            self.e_tel_min_target.set(64)

            self.e_tel_branch_k.set(2)
            self.cb_tel_control.set(True)
            self.e_tel_control_k.set(1)
            self.e_tel_max_samples.set(5000)
            self.tel_expand.set("bfs")

            self.tel_band_schedule.set("constant")
            self.e_tel_smin_start.set(0.70)
            self.e_tel_smax_start.set(0.95)
            self.e_tel_smin_end.set(0.70)
            self.e_tel_smax_end.set(0.95)

            self.e_tel_lmin_start.set(0.15)
            self.e_tel_lmax_start.set(0.65)
            self.e_tel_lmin_end.set(0.15)
            self.e_tel_lmax_end.set(0.65)

            self.e_tel_attempts.set(25)
            self.e_tel_copyratio.set(0.20)
            self.tel_sem_backend.set("tfidf")
            self.e_tel_dedupe.set(96.0)

        self._on_tel_schedule_change()
        self._on_tel_bands_change()
        self._update_preview()
        self._log(f"Applied preset: {p}")

    # ------------------------------ Noise mode toggles ------------------------------

    def _on_mode_change(self) -> None:
        mode = self.gen_mode.get().strip()
        is_unstructured = mode == "unstructured"
        uses_generated_letters = mode in {"syllable", "letterfreq", "uniform"}

        if mode == "uniform" and not is_unstructured:
            self.e_alphabet.entry.configure(state="normal")
        else:
            self.e_alphabet.entry.configure(state="disabled")

        if mode == "syllable" and not is_unstructured:
            self.r_syllables.min_entry.configure(state="normal")
            self.r_syllables.max_entry.configure(state="normal")
        else:
            self.r_syllables.min_entry.configure(state="disabled")
            self.r_syllables.max_entry.configure(state="disabled")

        self.w_allow_double.configure(state="normal" if uses_generated_letters else "disabled")

        lang_state = "disabled" if is_unstructured else "normal"
        for w in [
            self.r_sentences.min_entry, self.r_sentences.max_entry,
            self.r_words.min_entry, self.r_words.max_entry,
            self.e_word_mean.entry, self.e_word_sd.entry,
            self.r_wordlen_bounds.min_entry, self.r_wordlen_bounds.max_entry,
            self.w_cap_start, self.e_proper_rate.entry, self.e_caps_rate.entry,
            self.e_comma_rate.entry, self.e_max_commas.entry,
            self.e_w_period.entry, self.e_w_q.entry, self.e_w_ex.entry,
            self.w_paras, self.r_para_every.min_entry, self.r_para_every.max_entry,
        ]:
            try:
                w.configure(state=lang_state)
            except Exception:
                pass

        un_state = "normal" if is_unstructured else "disabled"
        for w in [
            self.r_un_chars.min_entry, self.r_un_chars.max_entry,
            self.e_un_pool.entry,
            self.e_un_w_alnum.entry, self.e_un_w_punct.entry, self.e_un_w_space.entry, self.e_un_w_newline.entry,
            self.e_un_max_run.entry,
            self.w_un_tabs,
        ]:
            try:
                w.configure(state=un_state)
            except Exception:
                pass

        if is_unstructured and bool(self.cb_un_tabs.get()):
            self.e_un_tab_weight.entry.configure(state="normal")
        else:
            self.e_un_tab_weight.entry.configure(state="disabled")

        self._on_zipf_toggle()

    def _on_zipf_toggle(self) -> None:
        mode = self.gen_mode.get().strip()
        is_unstructured = mode == "unstructured"

        if is_unstructured:
            try:
                self.w_zipf_enable.configure(state="disabled")
            except Exception:
                pass
            state = "disabled"
        else:
            try:
                self.w_zipf_enable.configure(state="normal")
            except Exception:
                pass
            enabled = bool(self.cb_zipf.get())
            state = "normal" if enabled else "disabled"

        for w in [
            self.e_zipf_exp.entry,
            self.e_func_vocab.entry, self.e_cont_vocab.entry, self.e_ent_vocab.entry,
            self.r_ent_len.min_entry, self.r_ent_len.max_entry,
            self.e_ent_start_rate.entry, self.e_ent_noun_rate.entry,
        ]:
            try:
                w.configure(state=state)
            except Exception:
                pass

        try:
            self.w_pos_suffix.configure(state="disabled" if (is_unstructured or mode == "dictionary") else "normal")
        except Exception:
            pass

        if (self.dataset_method.get() or "noise").strip().lower() == "noise":
            self._update_preview()

    # ------------------------------ Noise config reading ------------------------------

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
        c.generator_mode = self.gen_mode.get().strip()

        if c.generator_mode != "unstructured":
            c.sentences_min, c.sentences_max = self.r_sentences.get_int_range(min_value=1, max_value=1_000_000)
            c.words_min, c.words_max = self.r_words.get_int_range(min_value=1, max_value=1_000_000)

            c.word_len_mean = self.e_word_mean.get_float(min_value=1.0, max_value=200.0)
            c.word_len_stdev = self.e_word_sd.get_float(min_value=0.0, max_value=200.0)
            c.word_len_min, c.word_len_max = self.r_wordlen_bounds.get_int_range(min_value=1, max_value=500)

            c.allow_double_letters = bool(self.cb_allow_double.get())
            c.syllables_min, c.syllables_max = self.r_syllables.get_int_range(min_value=1, max_value=20)
            c.uniform_alphabet = self.e_alphabet.get_str().strip() or "abcdefghijklmnopqrstuvwxyz"
        else:
            c.sentences_min = c.sentences_max = 1
            c.words_min = c.words_max = 1
            c.word_len_mean = 4.7
            c.word_len_stdev = 1.8
            c.word_len_min = 2
            c.word_len_max = 12
            c.allow_double_letters = False
            c.syllables_min = 1
            c.syllables_max = 4
            c.uniform_alphabet = "abcdefghijklmnopqrstuvwxyz"

        if c.generator_mode == "unstructured":
            c.unstructured_min_chars, c.unstructured_max_chars = self.r_un_chars.get_int_range(min_value=0, max_value=50_000_000)
            c.unstructured_pool = self.e_un_pool.get_str()
            c.unstructured_weight_alnum = self.e_un_w_alnum.get_float(min_value=0.0, max_value=1_000_000.0)
            c.unstructured_weight_punct = self.e_un_w_punct.get_float(min_value=0.0, max_value=1_000_000.0)
            c.unstructured_weight_space = self.e_un_w_space.get_float(min_value=0.0, max_value=1_000_000.0)
            c.unstructured_weight_newline = self.e_un_w_newline.get_float(min_value=0.0, max_value=1_000_000.0)
            c.unstructured_max_run = self.e_un_max_run.get_int(min_value=1, max_value=1_000_000)
            c.unstructured_allow_tabs = bool(self.cb_un_tabs.get())
            c.unstructured_tab_weight = self.e_un_tab_weight.get_float(min_value=0.0, max_value=1_000_000.0)

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

        if c.generator_mode not in {"syllable", "letterfreq", "uniform", "dictionary", "unstructured"}:
            raise ValueError("Generator mode is invalid.")

        if c.generator_mode == "dictionary":
            c.allow_double_letters = False
            c.pos_like_suffixes = False

        if c.generator_mode != "unstructured":
            if c.word_len_min > c.word_len_max:
                raise ValueError("Word length bounds are invalid.")
            if c.word_len_mean < c.word_len_min or c.word_len_mean > c.word_len_max:
                raise ValueError("Average word length should fall within the word length bounds.")
            if c.syllables_min > c.syllables_max:
                raise ValueError("Syllables per word bounds are invalid.")

        if c.generator_mode == "uniform":
            cleaned = "".join(ch for ch in c.uniform_alphabet if ch.isprintable() and not ch.isspace())
            if len(cleaned) < 2:
                raise ValueError("Alphabet must contain at least 2 printable non-space characters.")
            c.uniform_alphabet = cleaned

        if c.generator_mode == "unstructured":
            c.enable_zipf_reuse = False

            if c.unstructured_max_chars <= 0:
                raise ValueError("Unstructured max characters must be > 0.")

            cleaned_pool = "".join(ch for ch in (c.unstructured_pool or "") if ch.isprintable() and not ch.isspace())
            if not cleaned_pool:
                raise ValueError("Unstructured char pool must contain at least 1 printable non-space character.")
            c.unstructured_pool = cleaned_pool

            weights = [
                max(0.0, float(c.unstructured_weight_alnum)),
                max(0.0, float(c.unstructured_weight_punct)),
                max(0.0, float(c.unstructured_weight_space)),
                max(0.0, float(c.unstructured_weight_newline)),
            ]
            if c.unstructured_allow_tabs and float(c.unstructured_tab_weight) > 0:
                weights.append(max(0.0, float(c.unstructured_tab_weight)))

            if sum(weights) <= 0:
                raise ValueError("Unstructured weights must include at least one positive value.")

            if c.unstructured_max_run < 1:
                raise ValueError("Unstructured max run length must be ≥ 1.")

        return c

    def _make_generator(self) -> NoiseTextGenerator:
        cfg = self._read_cfg_from_ui()
        if cfg.seed:
            random.seed(cfg.seed)
        else:
            random.seed(None)
        return NoiseTextGenerator(cfg)

    # ------------------------------ Telephone config reading ------------------------------

    def _read_tel_cfg_from_ui(self) -> TelephoneConfig:
        t = TelephoneConfig()

        t.seed_source_mode = (self.tel_seed_source.get() or "folder").strip().lower()
        t.seed_path = (self.tel_seed_path.get() or "").strip()
        t.seed_split_mode = (self.tel_seed_split.get() or "whole_file").strip().lower()
        t.fixed_chunk_chars = self.e_tel_chunk_chars.get_int(min_value=200, max_value=5_000_000)
        t.max_roots = self.e_tel_max_roots.get_int(min_value=1, max_value=1_000_000)
        t.shuffle_roots = bool(self.cb_tel_shuffle.get())

        t.include_control = bool(self.cb_tel_control.get())
        t.control_children_per_hop = self.e_tel_control_k.get_int(min_value=0, max_value=1_000_000)

        t.depth = self.e_tel_depth.get_int(min_value=1, max_value=100)
        t.branching_factor = self.e_tel_branch_k.get_int(min_value=0, max_value=1_000_000)
        t.max_samples_total = self.e_tel_max_samples.get_int(min_value=1, max_value=50_000_000)
        t.expansion_strategy = (self.tel_expand.get() or "bfs").strip().lower()

        t.length_schedule_mode = (self.tel_len_mode.get() or "mdic").strip().lower()
        t.geometric_first_target = self.e_tel_geo_first.get_int(min_value=1, max_value=50_000_000)
        t.geometric_ratio = self.e_tel_geo_ratio.get_float(min_value=0.05, max_value=0.95)
        t.custom_targets_csv = self.e_tel_custom_targets.get_str().strip()

        t.slack_mode = (self.tel_slack_mode.get() or "mdic").strip().lower()
        t.slack_percent = self.e_tel_slack_pct.get_float(min_value=0.0, max_value=0.5)
        t.slack_fixed = self.e_tel_slack_fixed.get_int(min_value=0, max_value=50_000_000)
        t.min_target_len = self.e_tel_min_target.get_int(min_value=1, max_value=50_000_000)

        t.band_schedule_mode = (self.tel_band_schedule.get() or "constant").strip().lower()
        t.s_min_start = self.e_tel_smin_start.get_float(min_value=0.0, max_value=1.0)
        t.s_max_start = self.e_tel_smax_start.get_float(min_value=0.0, max_value=1.0)
        t.s_min_end = self.e_tel_smin_end.get_float(min_value=0.0, max_value=1.0)
        t.s_max_end = self.e_tel_smax_end.get_float(min_value=0.0, max_value=1.0)

        t.l_min_start = self.e_tel_lmin_start.get_float(min_value=0.0, max_value=1.0)
        t.l_max_start = self.e_tel_lmax_start.get_float(min_value=0.0, max_value=1.0)
        t.l_min_end = self.e_tel_lmin_end.get_float(min_value=0.0, max_value=1.0)
        t.l_max_end = self.e_tel_lmax_end.get_float(min_value=0.0, max_value=1.0)

        t.max_attempts_per_child = self.e_tel_attempts.get_int(min_value=1, max_value=100_000)
        t.max_ngram_copy_ratio = self.e_tel_copyratio.get_float(min_value=0.0, max_value=1.0)

        t.semantic_backend = (self.tel_sem_backend.get() or "tfidf").strip().lower()
        t.dedupe_threshold = self.e_tel_dedupe.get_float(min_value=0.0, max_value=100.0)

        t.export_jsonl = bool(self.cb_tel_jsonl.get())
        t.jsonl_filename = self.e_tel_jsonl_name.get_str().strip() or f"telephone_tree_{date_val}.jsonl"
        t.export_txt_nodes = bool(self.cb_tel_txt.get())

        if not t.export_jsonl and not t.export_txt_nodes:
            raise ValueError("Telephone mode: enable JSONL export and/or TXT export (otherwise nothing will be written).")

        if t.expansion_strategy not in {"bfs", "dfs", "random"}:
            raise ValueError("Telephone mode: expansion strategy must be bfs/dfs/random.")

        if t.length_schedule_mode not in {"mdic", "geometric", "custom"}:
            raise ValueError("Telephone mode: schedule mode must be mdic/geometric/custom.")

        if t.slack_mode not in {"mdic", "percent", "fixed"}:
            raise ValueError("Telephone mode: slack mode must be mdic/percent/fixed.")

        if t.band_schedule_mode not in {"constant", "linear"}:
            raise ValueError("Telephone mode: band schedule must be constant/linear.")

        return t

    # ------------------------------ Preview ------------------------------

    def _update_preview(self) -> None:
        method = (self.dataset_method.get() or "noise").strip().lower()
        if method == "telephone":
            self._update_preview_telephone()
            return

        try:
            gen = self._make_generator()
            txt = gen.generate_document()
            self.preview.delete("1.0", "end")
            self.preview.insert("end", txt)
        except Exception as e:
            self._log(f"[Preview error] {e}")

    def _update_preview_telephone(self) -> None:
        try:
            tel_cfg = self._read_tel_cfg_from_ui()
        except Exception as e:
            self.preview.delete("1.0", "end")
            self.preview.insert("end", f"Telephone mode: {e}\n")
            return

        p = Path((tel_cfg.seed_path or "").strip()).expanduser()
        if not p.exists():
            self.preview.delete("1.0", "end")
            self.preview.insert("end", "Telephone mode preview:\n\nSelect a seed folder or .txt file to preview.\n")
            return

        try:
            tmp = TelephoneConfig(**asdict(tel_cfg))
            tmp.max_roots = 1
            tmp.max_samples_total = 100
            builder = TelephoneCascadeBuilder(tmp, log_fn=lambda _m: None)
            roots = builder.load_roots()
            root_id, root_text, meta = roots[0]
            targets, slacks = builder.build_schedule()

            hop1 = builder._generate_child_with_retries(parent_text=root_text, hop=1, target_chars=targets[1], slack_chars=slacks[1])
            hop2 = None
            if hop1 and tmp.depth >= 2:
                hop2 = builder._generate_child_with_retries(parent_text=hop1, hop=2, target_chars=targets[2], slack_chars=slacks[2])

            self.preview.delete("1.0", "end")
            self.preview.insert("end", f"[ROOT] ({meta.get('source','')})\n")
            self.preview.insert("end", root_text[:1500] + ("\n\n" if len(root_text) > 0 else ""))

            if hop1:
                sim1 = builder.scorer.similarity(root_text, hop1)
                lex1 = _lexical_overlap_jaccard(root_text, hop1)
                copy1 = _ngram_copy_ratio(root_text, hop1)
                self.preview.insert("end", f"\n[HOP 1] target≈{targets[1]}±{slacks[1]} | sim={sim1:.3f} | lex={lex1:.3f} | copy4={copy1:.3f}\n")
                self.preview.insert("end", hop1 + "\n")

            if hop2:
                sim2 = builder.scorer.similarity(hop1, hop2)
                lex2 = _lexical_overlap_jaccard(hop1, hop2)
                copy2 = _ngram_copy_ratio(hop1, hop2)
                self.preview.insert("end", f"\n[HOP 2] target≈{targets[2]}±{slacks[2]} | sim={sim2:.3f} | lex={lex2:.3f} | copy4={copy2:.3f}\n")
                self.preview.insert("end", hop2 + "\n")

        except Exception as e:
            self.preview.delete("1.0", "end")
            self.preview.insert("end", f"Telephone mode preview error:\n{e}\n")

    # ------------------------------ File generation ------------------------------

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
        method = (self.dataset_method.get() or "noise").strip().lower()
        if method == "telephone":
            return self._generate_telephone_dataset()
        return self._generate_noise_files()

    def _generate_noise_files(self) -> None:
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
                "dataset_method": "noise",
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

    def _generate_telephone_dataset(self) -> None:
        try:
            tel_cfg = self._read_tel_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Invalid telephone settings", str(e))
            return

        out = Path(self.out_dir.get().strip() or ".").expanduser().resolve()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Cannot create output folder", f"{out}\n\n{e}")
            return

        seed = self.e_seed.get_str().strip()
        if seed:
            random.seed(seed)
        else:
            random.seed(None)

        prefix = self.e_prefix.get_str()
        suffix = self.e_suffix.get_str()
        start_index = self.e_start_index.get_int(min_value=0, max_value=1_000_000_000)
        pad = self.e_pad.get_int(min_value=0, max_value=20)
        ext = self._normalize_extension(self.e_ext.get_str())
        overwrite = bool(self.cb_overwrite.get())

        export_settings_json = bool(self.cb_export_json.get())
        settings_filename = self.e_json_name.get_str().strip() or "dataset_settings.json"
        if not settings_filename.lower().endswith(".json"):
            settings_filename += ".json"
        include_file_list = bool(self.cb_json_filelist.get())

        if not tel_cfg.export_jsonl:
            tel_cfg.jsonl_filename = ""

        self._log(f"Output folder: {out}")
        self._log("Generating telephone tree dataset…")
        self._log(f"Seed: {seed or '(random)'}")

        try:
            builder = TelephoneCascadeBuilder(tel_cfg, log_fn=self._log)
            result = builder.build(
                out,
                output_prefix=prefix,
                output_suffix=suffix,
                start_index=start_index,
                zero_pad_width=pad,
                extension=ext,
                overwrite=overwrite,
                export_settings_json=export_settings_json,
                settings_filename=settings_filename,
                include_file_list=include_file_list,
            )
        except Exception as e:
            messagebox.showerror("Telephone generation failed", str(e))
            self._log(f"Telephone generation failed: {e}")
            return

        total = int(result.get("total_samples", 0) or 0)
        jsonl_path = result.get("jsonl")
        rej = result.get("rejected", {})

        self._log(f"Done. Wrote {total} sample(s).")
        if rej:
            self._log("Rejected counts (top reasons):")
            for k, v in sorted(rej.items(), key=lambda kv: -kv[1])[:12]:
                self._log(f"  {k}: {v}")

        msg = f"Wrote {total} sample(s) to:\n{out}"
        if jsonl_path:
            msg += f"\n\nJSONL: {Path(str(jsonl_path)).name}"
        messagebox.showinfo("Complete", msg)

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
