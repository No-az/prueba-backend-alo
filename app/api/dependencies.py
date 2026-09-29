"""Cableado de dependencias: aquí se decide qué adaptador recibe cada caso de uso."""

from typing import Annotated

from fastapi import Depends, Request

from app.application.ports import Clock, UnitOfWork
from app.application.use_cases import (
    GetApplication,
    GetEvaluationHistory,
    ListApplications,
    SubmitApplication,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_uow(request: Request) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


UowDep = Annotated[UnitOfWork, Depends(get_uow)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def submit_application(uow: UowDep, clock: ClockDep) -> SubmitApplication:
    return SubmitApplication(uow, clock)


def get_application(uow: UowDep) -> GetApplication:
    return GetApplication(uow)


def list_applications(uow: UowDep) -> ListApplications:
    return ListApplications(uow)


def get_evaluation_history(uow: UowDep) -> GetEvaluationHistory:
    return GetEvaluationHistory(uow)
