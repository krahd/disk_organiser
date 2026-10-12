import Foundation
import Security
import Darwin

struct ObservedHostIdentity: Sendable {
    let identifier: String
    let executablePath: String
    let codeDirectoryHash: Data
    let runningValidityChecked: Bool
}

enum HostIdentity {
    static let entitlementNames: Set<String> = [
        "com.apple.security.app-sandbox",
        "com.apple.security.files.user-selected.read-only",
    ]

    // This observes the calling process and validates its code before asking
    // for on-disk signing information. It does not accept a JSON entitlement
    // claim or equate successful dictionary retrieval with a valid signature.
    static func observe(expectedIdentifier: String, expectedExecutable: String) throws -> ObservedHostIdentity {
        var dynamic: SecCode?
        guard SecCodeCopySelf(SecCSFlags(), &dynamic) == errSecSuccess, let dynamic else {
            throw ProbeFailure.refused("self-code-unavailable")
        }
        return try inspect(dynamic, expectedIdentifier: expectedIdentifier, expectedExecutable: expectedExecutable)
    }

    // Used only by the separate UI runner for the exact, positively identified
    // launched probe. It does not search files or accept a bundle name as proof.
    static func observe(process: pid_t, expectedIdentifier: String, expectedExecutable: String) throws -> ObservedHostIdentity {
        guard process > 0 else { throw ProbeFailure.refused("invalid-process") }
        var dynamic: SecCode?
        let attributes = [kSecGuestAttributePid as String: NSNumber(value: process)] as CFDictionary
        guard SecCodeCopyGuestWithAttributes(nil, attributes, SecCSFlags(), &dynamic) == errSecSuccess,
              let dynamic else { throw ProbeFailure.refused("guest-code-unavailable") }
        return try inspect(dynamic, expectedIdentifier: expectedIdentifier, expectedExecutable: expectedExecutable)
    }

    private static func inspect(_ dynamic: SecCode, expectedIdentifier: String, expectedExecutable: String) throws -> ObservedHostIdentity {
        guard SecCodeCheckValidity(dynamic, SecCSFlags(rawValue: kSecCSStrictValidate), nil) == errSecSuccess else {
            throw ProbeFailure.refused("running-signature-invalid")
        }
        var staticCode: SecStaticCode?
        guard SecCodeCopyStaticCode(dynamic, SecCSFlags(), &staticCode) == errSecSuccess,
              let staticCode else { throw ProbeFailure.refused("static-code-unavailable") }
        return try information(staticCode, runningValidityChecked: true,
                               expectedIdentifier: expectedIdentifier, expectedExecutable: expectedExecutable)
    }

    static func observeStatic(bundle: URL, expectedIdentifier: String, expectedExecutable: String) throws -> ObservedHostIdentity {
        var code: SecStaticCode?
        guard SecStaticCodeCreateWithPath(bundle as CFURL, SecCSFlags(), &code) == errSecSuccess, let code,
              SecStaticCodeCheckValidity(code, SecCSFlags(rawValue: kSecCSStrictValidate), nil) == errSecSuccess else {
            throw ProbeFailure.refused("static-signature-invalid")
        }
        // A static inspection deliberately makes no running-code status claim.
        return try information(code, runningValidityChecked: false, expectedIdentifier: expectedIdentifier,
                               expectedExecutable: expectedExecutable)
    }

    private static func information(_ staticCode: SecStaticCode, runningValidityChecked: Bool,
                                    expectedIdentifier: String, expectedExecutable: String) throws -> ObservedHostIdentity {
        var dictionary: CFDictionary?
        let flags = SecCSFlags(rawValue: kSecCSSigningInformation | kSecCSRequirementInformation)
        guard SecCodeCopySigningInformation(staticCode, flags, &dictionary) == errSecSuccess,
              let info = dictionary as? [String: Any],
              let identifier = info[kSecCodeInfoIdentifier as String] as? String,
              identifier == expectedIdentifier,
              let executable = info[kSecCodeInfoMainExecutable as String] as? URL,
              executable.isFileURL, executable.path == expectedExecutable,
              let digest = info[kSecCodeInfoUnique as String] as? Data,
              !digest.isEmpty, digest.count <= 64,
              let entitlements = info[kSecCodeInfoEntitlementsDict as String] as? [String: Any],
              Set(entitlements.keys) == entitlementNames else {
            throw ProbeFailure.refused("signature-identity-or-entitlement-set")
        }
        for value in entitlements.values {
            guard let number = value as? NSNumber,
                  CFGetTypeID(number) == CFBooleanGetTypeID(), number.boolValue else {
                throw ProbeFailure.refused("entitlement-not-true-boolean")
            }
        }
        return ObservedHostIdentity(identifier: identifier, executablePath: executable.path,
                                    codeDirectoryHash: digest, runningValidityChecked: runningValidityChecked)
    }
}
