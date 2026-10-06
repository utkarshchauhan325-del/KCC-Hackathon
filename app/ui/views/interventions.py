"""Operations & Interventions View - Redirects to unified Priority Queue & Interventions Command Center."""

from app.ui.views.priority_queue import render_priority_queue_and_interventions

def render_interventions(embedded: bool = False):
    """Render unified Priority Queue & Interventions view."""
    render_priority_queue_and_interventions()
