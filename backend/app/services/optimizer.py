"""Genetic-algorithm GCP configuration optimizer and transparent baselines."""

from __future__ import annotations

import random
from copy import deepcopy

from .spatial import score_selection


def _evaluate(genome, candidates, ring, spacing_m, access_radius_m, weights):
    selected = [candidates[index] for index in genome]
    return score_selection(selected, ring, spacing_m, access_radius_m, weights)


def _tournament(population, scores, rng):
    contenders = rng.sample(range(len(population)), k=min(3, len(population)))
    return population[max(contenders, key=lambda index: scores[index]["fitness"])]


def _crossover(parent_a, parent_b, count, candidate_count, rng):
    child = list(dict.fromkeys(parent_a + parent_b))
    rng.shuffle(child)
    child = child[:count]
    if len(child) < count:
        unused = [index for index in range(candidate_count) if index not in child]
        child.extend(rng.sample(unused, k=count - len(child)))
    return tuple(sorted(child))


def _mutate(genome, candidate_count, mutation_rate, rng):
    child = list(genome)
    if rng.random() < mutation_rate:
        replacement = rng.choice([index for index in range(candidate_count) if index not in child])
        child[rng.randrange(len(child))] = replacement
    return tuple(sorted(child))


def genetic_optimize(candidates, ring, request):
    count = min(request.gcp_count, len(candidates))
    if count < 3:
        raise ValueError("At least three candidate GCPs are required")
    rng = random.Random(request.seed)
    weights = request.weights.model_dump()
    population = [tuple(sorted(rng.sample(range(len(candidates)), count))) for _ in range(request.population_size)]
    best_genome = None
    best_score = None

    for _generation in range(request.generations):
        scores = [
            _evaluate(genome, candidates, ring, request.candidate_spacing_m, request.access_radius_m, weights)
            for genome in population
        ]
        order = sorted(range(len(population)), key=lambda index: scores[index]["fitness"], reverse=True)
        if best_score is None or scores[order[0]]["fitness"] > best_score["fitness"]:
            best_genome, best_score = population[order[0]], scores[order[0]]

        elite_count = max(2, len(population) // 10)
        next_population = [population[index] for index in order[:elite_count]]
        while len(next_population) < request.population_size:
            parent_a = _tournament(population, scores, rng)
            parent_b = _tournament(population, scores, rng)
            child = _mutate(
                _crossover(parent_a, parent_b, count, len(candidates), rng),
                len(candidates),
                request.mutation_rate,
                rng,
            )
            next_population.append(child)
        population = next_population

    return [candidates[index] for index in best_genome], best_score


def _farthest_point_baseline(candidates, count):
    """A deterministic spatial-only baseline, similar to a regular spread."""
    selected = [min(candidates, key=lambda item: (item["coordinate"][0], item["coordinate"][1]))]
    while len(selected) < count:
        remaining = [candidate for candidate in candidates if candidate not in selected]
        selected.append(
            max(
                remaining,
                key=lambda candidate: min(
                    (candidate["coordinate"][0] - chosen["coordinate"][0]) ** 2
                    + (candidate["coordinate"][1] - chosen["coordinate"][1]) ** 2
                    for chosen in selected
                ),
            )
        )
    return selected


def build_baselines(candidates, ring, request):
    """Return compact comparison metrics without storing a large experiment history."""
    count = min(request.gcp_count, len(candidates))
    rng = random.Random(request.seed)
    weights = request.weights.model_dump()
    random_scores = []
    for _ in range(5):
        selection = rng.sample(candidates, count)
        random_scores.append(
            score_selection(selection, ring, request.candidate_spacing_m, request.access_radius_m, weights)
        )
    average_random = {
        key: round(sum(score[key] for score in random_scores) / len(random_scores), 4)
        for key in random_scores[0]
    }
    grid_selection = _farthest_point_baseline(candidates, count)
    grid_score = score_selection(grid_selection, ring, request.candidate_spacing_m, request.access_radius_m, weights)

    spatial_weights = deepcopy(weights)
    spatial_weights["accessibility"] = 0
    spatial_score = score_selection(grid_selection, ring, request.candidate_spacing_m, request.access_radius_m, spatial_weights)
    return {"random_mean": average_random, "spatial_grid": grid_score, "spatial_only": spatial_score}

