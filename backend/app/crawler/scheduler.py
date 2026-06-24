"""Celery Beat schedule for the FIR crawler.

Weekly crawl fires every Monday at 02:00 UTC.
An 8-day sliding window per spider ensures no FIRs are missed at week
boundaries even if a run is delayed by up to 24 hours.

Start the beat scheduler:
  celery -A app.crawler.scheduler.celery_app beat --loglevel=info
"""
from celery.schedules import crontab

from app.crawler.tasks import celery_app

celery_app.conf.beat_schedule = {
    "weekly-fir-crawl": {
        "task": "crawler.crawl_all_states",
        "schedule": crontab(hour=2, minute=0, day_of_week="monday"),
        "options": {"expires": 3600 * 6},   # drop if not consumed within 6 h
    },
}

celery_app.conf.beat_max_loop_interval = 300   # re-evaluate schedule every 5 min
