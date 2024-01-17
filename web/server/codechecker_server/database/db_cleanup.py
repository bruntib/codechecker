# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains housekeeping routines that are used to remove expired, obsolete,
or dangling records from the database.
"""
from datetime import datetime, timedelta

import sqlalchemy

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Severity

from codechecker_common import util
from codechecker_common.logger import get_logger

from .database import DBSession
from .run_db_model import \
    AnalysisInfo, \
    BugPathEvent, BugReportPoint, \
    Comment, Checker, \
    File, FileContent, \
    Report, ReportAnalysisInfo, RunHistoryAnalysisInfo, RunLock

LOG = get_logger('server')
RUN_LOCK_TIMEOUT_IN_DATABASE = 30 * 60  # 30 minutes.
SQLITE_LIMIT_COMPOUND_SELECT = 500


def remove_expired_data(session_maker):
    """ Remove information that has timed out from the database. """
    remove_expired_run_locks(session_maker)


def remove_unused_data(session_maker):
    """ Remove dangling data (files, comments, etc.) from the database. """
    remove_unused_files(session_maker)
    remove_unused_comments(session_maker)
    remove_unused_analysis_info(session_maker)


def update_contextual_data(session_maker, context):
    """
    Updates information in the database that comes from potentially changing
    contextual configuration of the server package.
    """
    upgrade_severity_levels(session_maker, context.checker_labels)


def remove_expired_run_locks(session_maker):
    with DBSession(session_maker) as session:
        LOG.debug("Garbage collection of expired run locks started...")
        try:
            locks_expired_at = datetime.now() - timedelta(
                seconds=RUN_LOCK_TIMEOUT_IN_DATABASE)

            count = session.query(RunLock) \
                .filter(RunLock.locked_at < locks_expired_at) \
                .delete(synchronize_session=False)
            if count:
                LOG.debug("%d expired run locks deleted.", count)

            session.commit()

            LOG.debug("Garbage collection of expired run locks finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove expired run locks: %s", str(ex))


def remove_unused_files(session_maker):
    # File deletion is a relatively slow operation due to database cascades.
    # Removing files in big chunks prevents reaching a potential database
    # statement timeout. This hard-coded value is a safe choice according to
    # some measurements. Maybe this could be a command-line parameter. But in
    # the long terms we are planning to reduce cascade deletes by redesigning
    # bug_path_events and bug_report_points tables.
    CHUNK_SIZE = 500000

    with DBSession(session_maker) as session:
        LOG.debug("Garbage collection of dangling files started...")
        try:
            bpe_files = session.query(BugPathEvent.file_id) \
                .group_by(BugPathEvent.file_id) \
                .subquery()
            brp_files = session.query(BugReportPoint.file_id) \
                .group_by(BugReportPoint.file_id) \
                .subquery()

            files_to_delete = session.query(File.id) \
                .filter(File.id.notin_(bpe_files), File.id.notin_(brp_files))
            files_to_delete = map(lambda x: x[0], files_to_delete)

            total_count = 0
            for chunk in util.chunks(iter(files_to_delete), CHUNK_SIZE):
                q = session.query(File) \
                    .filter(File.id.in_(chunk))
                count = q.delete(synchronize_session=False)
                if count:
                    total_count += count

            if total_count:
                LOG.debug("%d dangling files deleted.", total_count)

            files = session.query(File.content_hash) \
                .group_by(File.content_hash) \
                .subquery()

            session.query(FileContent) \
                .filter(FileContent.content_hash.notin_(files)) \
                .delete(synchronize_session=False)

            session.commit()

            LOG.debug("Garbage collection of dangling files finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove unused files: %s", str(ex))


def remove_unused_comments(session_maker):
    """ Remove dangling comments from the database. """
    with DBSession(session_maker) as session:
        LOG.debug("Garbage collection of dangling comments started...")
        try:
            report_hashes = session.query(Report.bug_id) \
                .group_by(Report.bug_id) \
                .subquery()

            count = session.query(Comment) \
                .filter(Comment.bug_hash.notin_(report_hashes)) \
                .delete(synchronize_session=False)
            if count:
                LOG.debug("%d dangling comments deleted.", count)

            session.commit()

            LOG.debug("Garbage collection of dangling comments finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove dangling comments: %s", str(ex))


def remove_unused_analysis_info(session_maker):
    """ Remove unused analysis information from the database. """
    # Analysis info deletion is a relatively slow operation due to database
    # cascades. Removing files in smaller chunks prevents reaching a potential
    # database statement timeout. This hard-coded value is a safe choice
    # according to some measurements.
    CHUNK_SIZE = 500

    with DBSession(session_maker) as session:
        LOG.debug("Garbage collection of dangling analysis info started...")
        try:
            to_delete = session.query(AnalysisInfo.id) \
                .join(
                    RunHistoryAnalysisInfo,
                    RunHistoryAnalysisInfo.c.analysis_info_id ==
                    AnalysisInfo.id,
                    isouter=True) \
                .join(
                    ReportAnalysisInfo,
                    ReportAnalysisInfo.c.analysis_info_id == AnalysisInfo.id,
                    isouter=True) \
                .filter(
                    RunHistoryAnalysisInfo.c.analysis_info_id.is_(None),
                    ReportAnalysisInfo.c.analysis_info_id.is_(None))

            to_delete = map(lambda x: x[0], to_delete)

            total_count = 0
            for chunk in util.chunks(to_delete, CHUNK_SIZE):
                count = session.query(AnalysisInfo) \
                    .filter(AnalysisInfo.id.in_(chunk)) \
                    .delete(synchronize_session=False)
                if count:
                    total_count += count

            if total_count:
                LOG.debug("%d dangling analysis info deleted.", total_count)

            session.commit()

            LOG.debug("Garbage collection of dangling analysis info finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove dangling analysis info: %s", str(ex))


def upgrade_severity_levels(session_maker, checker_labels):
    """
    Updates the potentially changed severities at the reports.
    """
    LOG.debug("Upgrading severity levels started...")

    with DBSession(session_maker) as session:
        try:
            count = 0
            for analyzer in sorted(checker_labels.get_analyzers()):
                checkers_for_analyzer_in_database = session \
                    .query(Checker.id,
                           Checker.checker_name,
                           Checker.severity) \
                    .filter(Checker.analyzer_name == analyzer) \
                    .all()
                for checker_row in checkers_for_analyzer_in_database:
                    checker: str = checker_row.checker_name
                    old_severity_db: int = checker_row.severity
                    old_severity: str = \
                        Severity._VALUES_TO_NAMES[old_severity_db]
                    new_severity: str = \
                        checker_labels.severity(checker, analyzer)
                    new_severity_db: int = \
                        Severity._NAMES_TO_VALUES[new_severity]

                    if old_severity_db == new_severity_db:
                        continue

                    LOG.info("Upgrading the severity level of checker "
                             "'%s/%s' from '%s' (%d) to '%s' (%d).",
                             analyzer, checker,
                             old_severity, old_severity_db,
                             new_severity, new_severity_db)
                    session.query(Checker) \
                        .filter(Checker.id == checker_row.id) \
                        .update({Checker.severity: new_severity_db})
                    count += 1

            if count:
                LOG.debug("%d checker severities upgraded.", count)

            session.commit()
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to upgrade severity levels: %s", str(ex))

    LOG.debug("Upgrading severity levels finished.")
