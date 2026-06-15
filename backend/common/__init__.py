"""Shared library imported by every microservice.

Add `backend/` to PYTHONPATH (start_all.sh does this) so each service can do
`from common.security import get_current_user`, etc.
"""
