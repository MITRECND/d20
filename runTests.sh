#!/bin/bash
set -e

/usr/bin/env pytest --cov-report term-missing --cov d20 -v
