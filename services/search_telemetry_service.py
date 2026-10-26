import logging
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from extensions import db
from models.search_event import SearchEvent


logger = logging.getLogger(__name__)


def record_search_event(
    *,
    query_original,
    query_normalized,
    total_results,
    returned_count,
    page_number,
    page_size,
    sort_option,
    team_filter=None,
    source_filter=None,
):
    session_class = sessionmaker(bind=db.engine, expire_on_commit=False)
    session = session_class()
    event = SearchEvent(
        query_original=query_original,
        query_normalized=query_normalized,
        searched_at=datetime.now(timezone.utc),
        total_results=total_results,
        returned_count=returned_count,
        page_number=page_number,
        page_size=page_size,
        sort_option=sort_option,
        team_filter=team_filter,
        source_filter=source_filter,
        no_results=total_results == 0,
    )
    try:
        session.add(event)
        session.commit()
        return True
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Search telemetry write failed (%s).", type(exc).__name__)
        return False
    finally:
        session.close()


def recent_search_stats(limit=10):
    event_count = db.session.query(func.count(SearchEvent.id)).scalar() or 0
    zero_result_count = (
        db.session.query(func.count(SearchEvent.id))
        .filter(SearchEvent.no_results.is_(True))
        .scalar()
        or 0
    )
    recent_events = (
        SearchEvent.query.order_by(SearchEvent.searched_at.desc(), SearchEvent.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "event_count": event_count,
        "zero_result_count": zero_result_count,
        "recent_events": recent_events,
    }
