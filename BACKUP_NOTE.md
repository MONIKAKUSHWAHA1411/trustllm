# Staging copy

This directory is a durable copy of the standalone project that belongs at
https://github.com/MONIKAKUSHWAHA1411/indic-name-bench

It lives here only because this session's git proxy was not authorised to push
to that repository. It is self-contained (own `pyproject.toml`, tests, data)
and can be lifted out with:

    git subtree split --prefix=indic-name-bench -b indic-name-bench-main
    git push git@github.com:MONIKAKUSHWAHA1411/indic-name-bench.git indic-name-bench-main:main

Delete this directory from `trustllm` once the standalone repo has the history.
