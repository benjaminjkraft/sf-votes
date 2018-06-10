#!/usr/bin/env python3
import collections
import itertools


def get_candidates(masterlookup_filename, contest_id):
    """Returns map of id to name."""
    candidates = {}
    with open(masterlookup_filename) as f:
        for line in f:
            if line[:10].strip() == 'Candidate' and line[74:81] == contest_id:
                candidates[line[10:17]] = candidates[17:67].strip()
    return candidates


class Ballot:
    def __init__(self):
        self.votes = [None, None, None]

    def add_ballotimage_line(self, line, candidates, precincts):
        self.precinct = precincts[line[26:33]]
        rank = int(line[33:36].lstrip('0')) - 1
        if line[43] == '1':
            self.votes[rank] = 'OVER'
        elif line[44] == '1':
            self.votes[rank] = None
        else:
            self.votes[rank] = candidates[line[36:43]]

    def cleaned_votes(self):
        votes = []
        for v in self.votes:
            if v == 'OVER':
                break
            elif v and v not in votes:
                votes.append(v)
        return votes


def get_ballots(filename_prefix='/home/benkraft/Downloads/20180609',
                contest_id='0000020'):  # mayor
    """Returns list of ballots."""
    candidates = {}
    precincts = {}
    with open(filename_prefix + '_masterlookup.txt') as f:
        for line in f:
            if line[:10].strip() == 'Candidate' and line[74:81] == contest_id:
                candidates[line[10:17]] = line[17:67].strip()
            elif line[:10].strip() == 'Precinct':
                precincts[line[10:17]] = line[17:67].strip()

    ballots = collections.defaultdict(Ballot)
    with open(filename_prefix + '_ballotimage.txt') as f:
        for line in f:
            if line[:7] == contest_id:
                ballots[line[7:16]].add_ballotimage_line(
                    line, candidates, precincts)

    return list(ballots.values())


def run_irv(ballots, verbose=True):
    votes = [b.cleaned_votes() for b in ballots]
    for i in itertools.count(1):
        nonexhausted = len(list(filter(None, votes)))
        totals = collections.Counter(
            v[0] for v in votes if v).most_common()

        if verbose:
            print("---------- ROUND %s (%s ballots) ----------"
                  % (i, nonexhausted))
            for c, v in totals:
                print(("%s:" % c).ljust(25), "%6s" % v)

        c, v = totals[0]
        if v > nonexhausted / 2:
            if verbose:
                print("Winner: %s (%s votes)" % (c, v))
            return c

        if verbose:
            eliminated = totals[-1][0]
            nexts = collections.Counter(
                v[1] if len(v) >= 2 else None
                for v in votes if v and v[0] == eliminated).most_common()
            print()
            print("%s eliminated!" % eliminated)
            for c, v in nexts:
                if c:
                    print("%6s -> %s" % (v, c))
                else:
                    print("%6s exhausted" % v)

        for v in votes:
            while eliminated in v:
                v.remove(eliminated)


def pairwise_preferences(ballots):
    candidates = set()
    votes = [b.cleaned_votes() for b in ballots]
    for v in votes:
        candidates.update(v)

    prefs = {}
    for a in candidates:
        for b in candidates:
            if a != b:
                prefs[(a, b)] = 0

    for v in votes:
        for i, c in enumerate(v):
            for d in v[i + 1:]:
                prefs[(c, d)] += 1
            for d in candidates - set(v):
                prefs[(c, d)] += 1

    return prefs


def run_condorcet(ballots, verbose=True, pref_fn=pairwise_preferences):
    prefs = pref_fn(ballots)
    candidates = {c for c, _ in prefs}
    wins = {c: len([c for d in candidates
                    if c != d and prefs[(c, d)] > prefs[(d, c)]])
            for c in candidates}

    if verbose:
        print("Ordering (best to worst):")
        for i in range(len(candidates) - 1, -1, -1):
            cs = [c for c, w in wins.items() if w == i]
            if len(cs) > 1:
                print(", ".join(cs), "(tie)")
            elif cs:
                print(cs[0])

    for c, w in wins.items():
        if w == len(candidates) - 1:
            return c


def _strongest_paths(ballots):
    prefs = pairwise_preferences(ballots)
    candidates = {c for c, _ in prefs}
    paths = {}
    for c in candidates:
        for d in candidates:
            if c != d:
                if prefs[(c, d)] > prefs[(d, c)]:
                    paths[(c, d)] = prefs[(c, d)]
                else:
                    paths[(c, d)] = 0

    for c in candidates:
        for d in candidates:
            if c != d:
                for e in candidates:
                    if e not in (c, d):
                        paths[(d, e)] = max(paths[(d, e)],
                                            min(paths[(d, c)], paths[(c, e)]))

    return paths


def run_schulze(ballots, verbose=True):
    return run_condorcet(ballots, verbose, _strongest_paths)
