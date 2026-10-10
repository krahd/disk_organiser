import XCTest
import Foundation
import Darwin
@testable import DiskInventoryDesktop

@MainActor
final class ApplicationLibraryACLTests: XCTestCase {
    func testOwnedDescriptorAbsentACLIsAdmittedAfterSuccessfulExtendedStat() throws {
        let fixture = try OwnedStorageFixture(), fd = try fixture.rejectionDescriptor()
        defer { Darwin.close(fd) }
        let security = try XCTUnwrap(filesec_init()); defer { filesec_free(security) }
        var info = stat(), present: Int32 = -1
        XCTAssertEqual(fstatx_np(fd, &info, security), 0)
        XCTAssertEqual(filesec_query_property(security, FILESEC_ACL, &present), 0)
        XCTAssertEqual(present, 0, "Fixture must actually establish the absent-ACL branch")
        try ApplicationLibraryIO().requireEmptyACL(fd); try fixture.assertSentinel()
    }
    func testInMemoryEmptyACLUsesNonOnePresenceBitAndIsAdmitted() throws {
        let security = try XCTUnwrap(filesec_init()); defer { filesec_free(security) }
        var acl: acl_t? = try XCTUnwrap(acl_init(0))
        defer { if let acl { _ = acl_free(UnsafeMutableRawPointer(acl)) } }
        XCTAssertEqual(filesec_set_property(security, FILESEC_ACL, &acl), 0)
        var present: Int32 = 0
        XCTAssertEqual(filesec_query_property(security, FILESEC_ACL, &present), 0)
        XCTAssertNotEqual(present, 0); XCTAssertNotEqual(present, 1)
        let empty = try XCTUnwrap(acl)
        XCTAssertEqual(acl_valid(empty), 0)
        var first: acl_entry_t?
        errno = 0
        XCTAssertEqual(acl_get_entry(empty, Int32(ACL_FIRST_ENTRY.rawValue), &first), -1)
        XCTAssertEqual(errno, EINVAL); XCTAssertNil(first)
        try ApplicationLibraryIO().requireEmptyACLMetadata(security)
        // This is actual in-memory Darwin API behaviour, not a claim that a
        // filesystem ACL was changed or a user permission was granted.
    }
    func testInMemoryNonemptyDenyACLIsRefusedWithoutChangingFilesystemPermissions() throws {
        let security = try XCTUnwrap(filesec_init()); defer { filesec_free(security) }
        var acl: acl_t? = try XCTUnwrap(acl_init(1))
        defer { if let acl { _ = acl_free(UnsafeMutableRawPointer(acl)) } }
        var entry: acl_entry_t?
        XCTAssertEqual(acl_create_entry(&acl, &entry), 0)
        let admitted = try XCTUnwrap(entry)
        XCTAssertEqual(acl_set_tag_type(admitted, ACL_EXTENDED_DENY), 0)
        var qualifier = UUID().uuid
        let qualifierResult = withUnsafePointer(to: &qualifier) { acl_set_qualifier(admitted, $0) }
        XCTAssertEqual(qualifierResult, 0)
        var permissions: acl_permset_t?
        XCTAssertEqual(acl_get_permset(admitted, &permissions), 0)
        XCTAssertEqual(acl_add_perm(try XCTUnwrap(permissions), ACL_READ_DATA), 0)
        let nonempty = try XCTUnwrap(acl)
        XCTAssertEqual(acl_valid(nonempty), 0)
        var first: acl_entry_t?
        XCTAssertEqual(acl_get_entry(nonempty, Int32(ACL_FIRST_ENTRY.rawValue), &first), 0)
        XCTAssertNotNil(first)
        XCTAssertEqual(filesec_set_property(security, FILESEC_ACL, &acl), 0)
        XCTAssertThrowsError(try ApplicationLibraryIO().requireEmptyACLMetadata(security))
    }
    func testInvalidDescriptorCannotBeTreatedAsAbsentACL() {
        XCTAssertThrowsError(try ApplicationLibraryIO().requireEmptyACL(-1))
    }
}
