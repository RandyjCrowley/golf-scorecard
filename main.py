"""Golf scorecard API and static frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

import database as db

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"


class Hole(BaseModel):
    holeNumber: int = Field(..., ge=1)
    par: int = Field(..., ge=1)
    score: int = Field(..., ge=1)


class RoundCreate(BaseModel):
    courseName: str = Field(..., min_length=1)
    playerName: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    holes: list[Hole] = Field(..., min_length=1)

    @model_validator(mode="after")
    def holes_must_be_nine_or_eighteen_and_sequential(self) -> RoundCreate:
        n = len(self.holes)
        if n not in (9, 18):
            raise ValueError("holes must contain exactly 9 or 18 holes")
        for i, h in enumerate(self.holes, start=1):
            if h.holeNumber != i:
                raise ValueError("holeNumber must be sequential from 1 through n")
        return self


class Round(BaseModel):
    id: str
    courseName: str
    playerName: str
    date: str
    holes: list[Hole]
    totalPar: int
    totalScore: int
    relativeToPar: int


class HealthResponse(BaseModel):
    status: str
    database: str


class StatsSummary(BaseModel):
    roundCount: int
    averageRelativeToPar: Optional[float]
    averageTotalScore: Optional[float]
    totalHolesPlayed: int


class PlayerLeaderboardEntry(BaseModel):
    playerName: str
    roundsPlayed: int
    averageRelativeToPar: Optional[float]
    firstRoundDate: str
    lastRoundDate: str


class RoundCountResponse(BaseModel):
    count: int


class RoundsPage(BaseModel):
    items: list[Round]
    total: int
    limit: int
    offset: int


app = FastAPI(title="Golf Scorecard", description="Backend-focused learning API with SQLite.")


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "index.html")


def _hole_models(data: list[dict]) -> list[Hole]:
    return [Hole(**h) for h in data]


def _round_from_db(r: dict) -> Round:
    return Round(
        id=r["id"],
        courseName=r["courseName"],
        playerName=r["playerName"],
        date=r["date"],
        holes=_hole_models(r["holes"]),
        totalPar=r["totalPar"],
        totalScore=r["totalScore"],
        relativeToPar=r["relativeToPar"],
    )


def _list_filters(
    player_name: Optional[str],
    course_name: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> dict:
    return {
        "player_name": player_name,
        "course_contains": course_name,
        "date_from": date_from,
        "date_to": date_to,
    }


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    if not db.ping_db():
        raise HTTPException(status_code=503, detail="Database unavailable")
    return HealthResponse(status="ok", database="up")


@app.get("/api/stats/summary", response_model=StatsSummary, tags=["stats"])
def stats_summary() -> StatsSummary:
    row = db.get_stats_summary()
    return StatsSummary(**row)


@app.get(
    "/api/stats/players",
    response_model=list[PlayerLeaderboardEntry],
    tags=["stats"],
)
def player_leaderboard() -> list[PlayerLeaderboardEntry]:
    return [PlayerLeaderboardEntry(**r) for r in db.get_player_leaderboard()]


@app.get("/api/rounds", response_model=list[Round], tags=["rounds"])
def list_rounds(
    playerName: Optional[str] = Query(
        None, description="Case-insensitive substring match on player name"
    ),
    courseName: Optional[str] = Query(
        None, description="Case-insensitive substring match on course name"
    ),
    date_from: Annotated[
        Optional[str],
        Query(alias="from", description="Inclusive lower date bound (YYYY-MM-DD text)"),
    ] = None,
    date_to: Annotated[
        Optional[str],
        Query(alias="to", description="Inclusive upper date bound (YYYY-MM-DD text)"),
    ] = None,
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=500,
        description="Optional page size (omit for all matching rows, up to query cost)",
    ),
    offset: int = Query(0, ge=0),
) -> list[Round]:
    f = _list_filters(playerName, courseName, date_from, date_to)
    rows = db.get_rounds(limit=limit, offset=offset, **f)
    return [_round_from_db(r) for r in rows]


@app.get("/api/rounds/count", response_model=RoundCountResponse, tags=["rounds"])
def rounds_count(
    playerName: Optional[str] = None,
    courseName: Optional[str] = None,
    date_from: Annotated[Optional[str], Query(alias="from")] = None,
    date_to: Annotated[Optional[str], Query(alias="to")] = None,
) -> RoundCountResponse:
    f = _list_filters(playerName, courseName, date_from, date_to)
    return RoundCountResponse(count=db.count_rounds(**f))


@app.get("/api/rounds/page", response_model=RoundsPage, tags=["rounds"])
def list_rounds_page(
    playerName: Optional[str] = None,
    courseName: Optional[str] = None,
    date_from: Annotated[Optional[str], Query(alias="from")] = None,
    date_to: Annotated[Optional[str], Query(alias="to")] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> RoundsPage:
    f = _list_filters(playerName, courseName, date_from, date_to)
    total = db.count_rounds(**f)
    rows = db.get_rounds(limit=limit, offset=offset, **f)
    return RoundsPage(
        items=[_round_from_db(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post("/api/rounds", response_model=Round, status_code=201, tags=["rounds"])
def create_round(payload: RoundCreate) -> Round:
    holes_data = [h.model_dump() for h in payload.holes]
    created = db.create_round(
        course_name=payload.courseName,
        player_name=payload.playerName,
        date=payload.date,
        holes=holes_data,
    )
    return _round_from_db(created)


@app.get("/api/rounds/{round_id}", response_model=Round, tags=["rounds"])
def get_round(round_id: str) -> Round:
    r = db.get_round_by_id(round_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return _round_from_db(r)


@app.put("/api/rounds/{round_id}", response_model=Round, tags=["rounds"])
def update_round(round_id: str, payload: RoundCreate) -> Round:
    holes_data = [h.model_dump() for h in payload.holes]
    updated = db.update_round(
        round_id=round_id,
        course_name=payload.courseName,
        player_name=payload.playerName,
        date=payload.date,
        holes=holes_data,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return _round_from_db(updated)


@app.delete("/api/rounds/{round_id}", tags=["rounds"])
def delete_round(round_id: str) -> dict:
    if not db.delete_round(round_id):
        raise HTTPException(status_code=404, detail="Round not found")
    return {"message": "Round deleted"}


app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")
