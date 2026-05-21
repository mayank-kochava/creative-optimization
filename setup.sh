#!/usr/bin/env bash
# Kochava Creative Optimiser — one-shot local install
# Supports: macOS (Homebrew), Ubuntu/Debian
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[setup]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo ""
echo -e "${BOLD}Kochava Creative Optimiser — Setup${NC}"
echo "======================================"
echo ""

# ── 1. OS detection ─────────────────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
elif [[ -f /etc/debian_version ]]; then
  OS="debian"
elif [[ -f /etc/redhat-release ]]; then
  die "Red Hat / CentOS detected. Install dependencies manually then re-run."
fi

info "Detected OS: $OS"

# ── 2. Homebrew (macOS) ──────────────────────────────────────────────────────
if [[ "$OS" == "macos" ]]; then
  if ! command -v brew &>/dev/null; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
fi

# ── 3. System packages ───────────────────────────────────────────────────────
install_pkg() {
  local pkg="$1"
  if [[ "$OS" == "macos" ]]; then
    if ! brew list "$pkg" &>/dev/null; then
      info "brew install $pkg"
      brew install "$pkg"
    fi
  elif [[ "$OS" == "debian" ]]; then
    if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
      info "apt-get install $pkg"
      sudo apt-get install -y "$pkg"
    fi
  fi
}

if [[ "$OS" == "debian" ]]; then
  info "Updating apt..."
  sudo apt-get update -qq
fi

install_pkg tesseract
install_pkg ffmpeg

# PostgreSQL client libs (needed for asyncpg on Linux)
if [[ "$OS" == "debian" ]]; then
  install_pkg libpq-dev
  install_pkg python3-dev
fi

success "System packages ready"

# ── 4. Python 3.11 ──────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3.11 python3 python; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major="${ver%%.*}"; minor="${ver##*.}"
    if [[ "$major" -eq 3 && "$minor" -ge 11 ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  if [[ "$OS" == "macos" ]]; then
    info "Installing Python 3.11 via Homebrew..."
    brew install python@3.11
    PYTHON="$(brew --prefix python@3.11)/bin/python3.11"
  elif [[ "$OS" == "debian" ]]; then
    info "Installing Python 3.11..."
    sudo apt-get install -y python3.11 python3.11-venv python3-pip
    PYTHON="python3.11"
  else
    die "Python 3.11+ not found. Install it then re-run."
  fi
fi
success "Python: $($PYTHON --version)"

# ── 5. Node.js 18+ ──────────────────────────────────────────────────────────
if ! command -v node &>/dev/null || [[ $(node -e "process.exit(parseInt(process.versions.node)<18?1:0)" 2>&1; echo $?) -ne 0 ]]; then
  if [[ "$OS" == "macos" ]]; then
    info "Installing Node.js via Homebrew..."
    brew install node
  elif [[ "$OS" == "debian" ]]; then
    info "Installing Node.js 18 via NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
  else
    die "Node.js 18+ not found. Install it then re-run."
  fi
fi
success "Node: $(node --version)"

# ── 6. Docker ────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  if [[ "$OS" == "macos" ]]; then
    die "Docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop/ then re-run."
  else
    die "Docker not found. Install Docker then re-run: https://docs.docker.com/engine/install/"
  fi
fi
if ! docker info &>/dev/null; then
  die "Docker daemon not running. Start Docker Desktop then re-run."
fi
success "Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"

# ── 7. Ollama (optional) ─────────────────────────────────────────────────────
OLLAMA_READY=false
if command -v ollama &>/dev/null && ollama list 2>/dev/null | grep -q "qwen2.5vl"; then
  OLLAMA_READY=true
  success "Ollama + qwen2.5vl:7b found (local fallback available)"
else
  if [[ "$OS" == "macos" ]] && ! command -v ollama &>/dev/null; then
    warn "Ollama not installed. Claude will be used as the AI provider."
    warn "To install Ollama as a local fallback: brew install ollama/tap/ollama && ollama pull qwen2.5vl:7b"
  elif command -v ollama &>/dev/null; then
    warn "Ollama found but qwen2.5vl:7b model not pulled. Run: ollama pull qwen2.5vl:7b"
  fi
fi

# ── 8. Python virtual environment ────────────────────────────────────────────
VENV_DIR="$REPO_ROOT/backend/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating Python virtual environment..."
  $PYTHON -m venv "$VENV_DIR"
fi
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
success "Virtual environment: $VENV_DIR"

info "Installing Python dependencies (this may take a minute)..."
$VENV_PIP install --quiet --upgrade pip
$VENV_PIP install --quiet -r "$REPO_ROOT/backend/requirements.txt"
success "Python dependencies installed"

# Symlink so Makefile's python3.11 calls also work via the venv
if [[ "$OS" == "macos" ]]; then
  VENV_BIN="$VENV_DIR/bin"
  if [[ ! -L "$VENV_BIN/python3.11" ]]; then
    ln -sf "$VENV_PYTHON" "$VENV_BIN/python3.11" 2>/dev/null || true
  fi
fi

# ── 9. Frontend dependencies ─────────────────────────────────────────────────
info "Installing frontend dependencies..."
cd "$REPO_ROOT/frontend" && npm install --silent
success "Frontend dependencies installed"
cd "$REPO_ROOT"

# ── 10. Environment file ─────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$REPO_ROOT/backend/.env.example" "$ENV_FILE"
  info "Created backend/.env from .env.example"
fi

# Prompt for API key if not already set
CURRENT_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
if [[ -z "$CURRENT_KEY" || "$CURRENT_KEY" == "sk-ant-..." ]]; then
  echo ""
  echo -e "${BOLD}Anthropic API Key${NC}"
  echo "The default AI provider is Claude Sonnet 4.6."
  echo "Get a key at: https://console.anthropic.com"
  echo ""
  read -rp "Paste your ANTHROPIC_API_KEY (press Enter to skip, use Ollama instead): " API_KEY
  if [[ -n "$API_KEY" ]]; then
    # Replace or append
    if grep -q '^ANTHROPIC_API_KEY=' "$ENV_FILE"; then
      sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
    else
      echo "ANTHROPIC_API_KEY=$API_KEY" >> "$ENV_FILE"
    fi
    success "API key saved to backend/.env"
  else
    if $OLLAMA_READY; then
      warn "Skipped. Using Ollama (qwen2.5vl:7b) as AI provider."
      sed -i.bak "s|^ANALYSIS_PROVIDER=.*|ANALYSIS_PROVIDER=ollama|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
    else
      warn "Skipped. Set ANTHROPIC_API_KEY in backend/.env before running make dev."
    fi
  fi
else
  success "API key already configured"
fi

# ── 11. PostgreSQL ────────────────────────────────────────────────────────────
info "Starting PostgreSQL..."
docker-compose up -d postgres
info "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 20); do
  if docker-compose exec -T postgres pg_isready -U appuser -d creative_opt &>/dev/null; then
    break
  fi
  sleep 1
done
success "PostgreSQL ready"

# ── 12. Database migrations ───────────────────────────────────────────────────
info "Running database migrations..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. "$VENV_DIR/bin/alembic" upgrade head
success "Migrations applied"

# ── 13. Benchmark corpus setup ───────────────────────────────────────────────
info "Setting up benchmark image corpus (downloading ~50 images from CVPR dataset)..."
PYTHONPATH=. "$VENV_PYTHON" scripts/setup_benchmark.py
success "Benchmark corpus ready"

# ── 14. Seed demo data ────────────────────────────────────────────────────────
info "Seeding demo campaigns and creatives..."
PYTHONPATH=. "$VENV_PYTHON" scripts/seed_data.py
success "Demo data seeded"

# ── 15. Pre-compute AI analysis ───────────────────────────────────────────────
CURRENT_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
if [[ -n "$CURRENT_KEY" && "$CURRENT_KEY" != "sk-ant-..." ]]; then
  info "Running AI analysis on demo creatives (3-5 min with Claude)..."
  PYTHONPATH=. "$VENV_PYTHON" scripts/precompute_analysis.py
  success "AI analysis complete"
else
  warn "Skipping AI analysis — no API key set. Run 'make seed' after adding your key."
fi

cd "$REPO_ROOT"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo "  Start the app:    make dev"
echo "  Frontend:         http://localhost:3000"
echo "  API docs:         http://localhost:8000/docs"
echo "  Stop servers:     make stop"
echo ""
if [[ -z "$CURRENT_KEY" || "$CURRENT_KEY" == "sk-ant-..." ]]; then
  echo -e "  ${YELLOW}Add your API key to backend/.env then run: make seed${NC}"
  echo ""
fi
