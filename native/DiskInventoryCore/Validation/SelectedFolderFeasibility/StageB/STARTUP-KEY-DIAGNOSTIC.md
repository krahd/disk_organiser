# Disabled startup environment-key diagnostic

Historical diagnostic contract: the strict-admission statements below describe the retained PR42 checkpoint. The later, still-disabled [fixed encoding-marker admission](ENCODING-MARKER-ADMISSION.md) supersedes only that key-set rule; the diagnostic schema and fixed presence Booleans remain unchanged.

## Observed limit

The one approved framework attempt at `9f189aa0` stopped at `startup environment keys` in [run 38328990361](https://github.com/krahd/disk_organiser/actions/runs/38328990361). The exact bootstrap had already passed its fixed interpreter-identity gate, but had not reached dispatch/workflow validation, operational imports or owner creation. The log contains neither the key difference nor a complete interpreter-facts record. It does not establish which environment key was missing or added.

PR41 deactivated that consumed attempt. Its marker remains intact. This diagnostic is disabled source only: profile False, no active workflow, no new reserved ref, no host or build execution. The fourth inert anchor retains the consumed framework ref; it grants no retry. Any future execution requires a separate concrete decision and reviewed source/trigger identity.

## Fixed disclosure schema

The existing exact key-set equality still refuses every extra or missing key. No locale, launcher, framework or security-related variable becomes an exception. Successful admission still copies only the same eighteen explicitly reviewed keys and retains every value bound and fixed PATH/LANG/LC_ALL check.

Only a key-set mismatch constructs `StartupEnvironmentRefusal`, a subtype of the existing refusal, with the same fixed message. The exception retains a detached primitive summary, not the environment or observed key set. The CLI emits this summary only for that exact exception type. Other refusals retain their existing record fields without the new summary. There is no fresh environment read in the exception handler.

`environment_keys` contains exactly:

- `schema`: integer 1.
- `missing_expected`: sorted names drawn solely from the fixed eighteen-name expected set. No arbitrary observed name is emitted.
- `unexpected_count`: integer 0–256; `unexpected_count_capped` is true exactly when the actual count exceeds 256.
- `known_system_presence`: four Boolean values for the literal names `LC_CTYPE`, `__PYVENV_LAUNCHER__`, `__CF_USER_TEXT_ENCODING` and `_`. Presence remains a refusal, never permission to inherit the variable.
- `unknown_count`: unexpected names outside those four, saturated at 256; `unknown_count_capped` explicitly records overflow.

No environment value, arbitrary unknown name, hash of an unknown name, path inferred from a value, token or secret is emitted or retained in the summary. Only fixed-set membership and counts are needed after the existing key-set observation. All field names and emitted name strings are fixed. The complete mismatch notice is tested within 2048 UTF-8 bytes, including conservatively maximal existing executable/platform/version fields. There is no truncation of expected omissions or fixed known-key observations; count saturation is explicit.

The mismatch still occurs before workflow reads, dispatch, source admission, operational imports and owner creation. No process, filesystem operation, environment mutation, native command, wait or retry is added. Both default controller gates and Stage C remain closed.

## Evidence versus hypotheses

[CPython 3.12.10's framework launcher](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Mac/Tools/pythonw.c#L202-L210) passes its identity in a launcher variable. [Its path initialisation](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Modules/getpath.c#L626-L680) supports removing environment inputs and [requests removal for that variable](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Modules/getpath.c#L899-L905). These source paths do not supply the failed runner's actual key set.

[CPython's locale code](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Python/pylifecycle.c#L175-L188) bypasses ordinary C-locale coercion when LC_ALL is nonempty; the fixed workflow supplies LC_ALL=C. This is a source constraint, not proof of the actual mismatch cause.

[Apple's published CoreFoundation source](https://github.com/apple-oss-distributions/CF/blob/dc54c6bb1c1e5e0b9486c1d26dd5bef110b20bf3/CFStringEncodings.c#L890-L950) contains an environment-setting path for user encoding. That repository snapshot is CF-1153.18, imported in 2015; it establishes a historical mechanism, not the implementation or executed path on the current macOS 15 runner. No compatibility exception is justified by this hypothesis.

## Source checks and remaining gate

Memory regressions cover every expected omission; each known-system presence still refusing; arbitrary/long/Unicode/non-string unknown keys; forbidden value access; exact 256/257 count boundaries; detached data; exact exception-type gating; maximum JSON shape/length; unchanged clean admission; and pre-import refusal ordering. The three historical anchors remain exact bytes. The new inert anchor changes only the normalised profile hash relative to the framework anchor; helper/host/command limits remain pinned.

These checks cannot observe the missing runtime facts. Source review and ordinary CI do not authorise or replace a fresh build-only attempt. The diagnostic must first receive independent source review. Never loosen admission or name an observed offending key until actual evidence establishes it.
