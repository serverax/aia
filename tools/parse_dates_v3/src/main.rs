//! parse_dates_v3 — extract date references from free text.
//!
//! Supports two patterns out of the box:
//!   * ISO: YYYY-MM-DD             (highest confidence)
//!   * Slash: DD/MM/YYYY (en-GB)   or MM/DD/YYYY (en-US)
//!
//! Real-world date parsing is hard. This is a Sprint 6 reference tool —
//! it proves the WASM pipeline works end-to-end, not that we have a
//! production-grade date parser. Production use should wrap a real
//! library (e.g. chrono / dateparser) once we know the tool catalog.

use aia_tool_sdk as sdk;
use once_cell::sync::Lazy;
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct Input {
    text: String,
    #[serde(default = "default_locale")]
    locale: String,
}

fn default_locale() -> String {
    "en-GB".to_string()
}

#[derive(Debug, Serialize)]
struct DateMatch {
    iso: String,
    raw: String,
    confidence: f64,
}

#[derive(Debug, Serialize)]
struct Output {
    dates: Vec<DateMatch>,
}

static ISO_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\b(\d{4})-(\d{2})-(\d{2})\b").unwrap());

static SLASH_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b").unwrap());

fn run(input: Input) -> Result<Output, String> {
    let mut dates: Vec<DateMatch> = Vec::new();

    for cap in ISO_RE.captures_iter(&input.text) {
        let (year, month, day) = (&cap[1], &cap[2], &cap[3]);
        if !valid_md(month, day) {
            continue;
        }
        dates.push(DateMatch {
            iso: format!("{year}-{month}-{day}"),
            raw: cap[0].to_string(),
            confidence: 0.98,
        });
    }

    let us = input.locale.eq_ignore_ascii_case("en-US");
    for cap in SLASH_RE.captures_iter(&input.text) {
        let (a, b, y) = (&cap[1], &cap[2], &cap[3]);
        let (day, month) = if us { (b, a) } else { (a, b) };
        if !valid_md(month, day) {
            continue;
        }
        dates.push(DateMatch {
            iso: format!("{y}-{:0>2}-{:0>2}", month, day),
            raw: cap[0].to_string(),
            confidence: 0.85,
        });
    }

    Ok(Output { dates })
}

fn valid_md(month: &str, day: &str) -> bool {
    let m: u32 = month.parse().unwrap_or(0);
    let d: u32 = day.parse().unwrap_or(0);
    (1..=12).contains(&m) && (1..=31).contains(&d)
}

sdk::tool_main!(Input, Output, run);
