;; A minimal WASI command module used in tests. It reads JSON from stdin
;; and writes it back to stdout verbatim. Compile with:
;;   wat2wasm echo.wat -o echo.wasm
;;
;; (Most environments don't have wat2wasm in CI, so the test suite ships
;;  the compiled echo.wasm alongside this source.)

(module
  (import "wasi_snapshot_preview1" "fd_read"  (func $fd_read  (param i32 i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_write" (func $fd_write (param i32 i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $exit (param i32)))

  (memory (export "memory") 1 16)

  (func $start (export "_start")
    (local $nread i32)
    (local $nwritten i32)

    ;; iovec at 0: buf=64, len=8000  (read up to 8000 bytes into addr 64)
    (i32.store        (i32.const 0) (i32.const 64))
    (i32.store offset=4 (i32.const 0) (i32.const 8000))
    ;; fd_read(0, iovs=0, iovs_len=1, nread=8)
    (drop (call $fd_read (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 8)))
    (local.set $nread (i32.load (i32.const 8)))

    ;; iovec at 16: buf=64, len=$nread  (write same buffer back)
    (i32.store         (i32.const 16) (i32.const 64))
    (i32.store offset=4 (i32.const 16) (local.get $nread))
    ;; fd_write(1, iovs=16, iovs_len=1, nwritten=24)
    (drop (call $fd_write (i32.const 1) (i32.const 16) (i32.const 1) (i32.const 24)))

    (call $exit (i32.const 0))
  )
)
