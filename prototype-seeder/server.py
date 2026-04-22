"""Prototype-seeder service.

Sole purpose: wrap init-prototype.sh behind an HTTP endpoint so that
hermes-agent and opencode — which have CAP_DAC_OVERRIDE dropped and so
cannot write into admin-owned /prototypes — can still request a slug
to be seeded. This container keeps CAP_DAC_OVERRIDE and is the only
process with write access to new subdirectories of /prototypes.
"""
import os
import re
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROTOTYPES_ROOT = Path("/prototypes")
INIT_SCRIPT = PROTOTYPES_ROOT / ".registry" / "init-prototype.sh"
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")

app = FastAPI(title="prototype-seeder", version="1.0.0")


class SeedRequest(BaseModel):
    slug: str = Field(..., description="lowercase slug, e.g. worlds-fair-companion")


class SeedResponse(BaseModel):
    slug: str
    port: int
    path: str


@app.get("/health")
def health():
    return {"status": "ok", "init_script_exists": INIT_SCRIPT.is_file()}


@app.post("/seed", response_model=SeedResponse)
def seed(req: SeedRequest):
    slug = req.slug.strip()
    if not SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="slug must match ^[a-z][a-z0-9-]{1,63}$ (lowercase, hyphens, no leading _/.)",
        )
    if not INIT_SCRIPT.is_file():
        raise HTTPException(status_code=500, detail=f"init script missing at {INIT_SCRIPT}")

    # init-prototype.sh prints the allocated port on stdout; errors go to stderr.
    result = subprocess.run(
        ["bash", str(INIT_SCRIPT), slug],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={"stderr": result.stderr.strip(), "stdout": result.stdout.strip(), "rc": result.returncode},
        )

    # Ensure slug dir is writable by root (hermes/opencode run as root but
    # without DAC_OVERRIDE — they need owner match to write).
    slug_dir = PROTOTYPES_ROOT / slug
    os.chown(slug_dir, 0, 0)
    for p in slug_dir.rglob("*"):
        try:
            os.chown(p, 0, 0)
        except OSError:
            pass

    port_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    try:
        port = int(port_line)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail=f"init-prototype.sh did not print a port; got {port_line!r}",
        )

    return SeedResponse(slug=slug, port=port, path=str(slug_dir))
