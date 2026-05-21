//! Shared helpers for AIA WASM tools.
//!
//! Tools follow a strict JSON-in / JSON-out contract:
//! - Stdin contains a single JSON value (the input).
//! - Stdout contains a single JSON object (the result).
//! - Stderr is for human-readable logs only and is not parsed.
//!
//! The `tool_main!` macro wraps this in a single line so each tool's
//! `main.rs` only carries the actual business logic.

use serde::{de::DeserializeOwned, Serialize};
use std::io::{self, Read, Write};
use std::process;

/// Read a JSON value from stdin and deserialize into `T`.
pub fn read_input<T: DeserializeOwned>() -> Result<T, String> {
    let mut buf = String::new();
    io::stdin()
        .read_to_string(&mut buf)
        .map_err(|e| format!("stdin read failed: {e}"))?;
    serde_json::from_str(&buf).map_err(|e| format!("stdin not valid JSON: {e}"))
}

/// Serialize `value` to JSON and write to stdout (no trailing newline).
pub fn write_output<T: Serialize>(value: &T) -> Result<(), String> {
    let bytes = serde_json::to_vec(value).map_err(|e| format!("serialize failed: {e}"))?;
    io::stdout()
        .write_all(&bytes)
        .map_err(|e| format!("stdout write failed: {e}"))?;
    Ok(())
}

/// Write an error envelope (`{"error": "..."}`) and exit non-zero.
///
/// The host treats non-zero exit + `error` field as a tool-level failure
/// (distinct from a host-level WASM trap).
pub fn fail(message: &str) -> ! {
    let err = serde_json::json!({ "error": message });
    let _ = write_output(&err);
    process::exit(1);
}

/// Generate `fn main()` for a tool given its input type, output type, and
/// the function that does the work.
///
/// ```ignore
/// use aia_tool_sdk as sdk;
///
/// #[derive(serde::Deserialize)] struct Input { text: String }
/// #[derive(serde::Serialize)]   struct Output { length: usize }
///
/// fn run(input: Input) -> Result<Output, String> {
///     Ok(Output { length: input.text.len() })
/// }
///
/// sdk::tool_main!(Input, Output, run);
/// ```
#[macro_export]
macro_rules! tool_main {
    ($input_ty:ty, $output_ty:ty, $run_fn:expr) => {
        fn main() {
            let input: $input_ty = match $crate::read_input() {
                Ok(v) => v,
                Err(e) => $crate::fail(&format!("invalid input: {}", e)),
            };
            let run: fn($input_ty) -> Result<$output_ty, String> = $run_fn;
            match run(input) {
                Ok(out) => {
                    if let Err(e) = $crate::write_output(&out) {
                        eprintln!("output error: {}", e);
                        std::process::exit(2);
                    }
                }
                Err(e) => $crate::fail(&e),
            }
        }
    };
}
