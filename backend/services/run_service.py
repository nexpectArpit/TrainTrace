"""Run read use-cases composed from persistence queries."""

from repositories.run_repository import comparison_page, get_run, search_exact_tag


def run_detail(run_id):
    return get_run(run_id)


def compare_runs(experiment_id, **filters):
    return comparison_page(experiment_id, **filters)


def search_tags(key=None, value=None, **filters):
    return search_exact_tag(key, value, **filters)
