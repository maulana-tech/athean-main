// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/erc8004/AgentPassport.sol";

contract AgentPassportTest is Test {
    AgentPassport passport;

    address admin = address(0xA1);
    address minter = address(0xB2);
    address user = address(0xC3);
    address user2 = address(0xD4);

    function setUp() public {
        passport = new AgentPassport(admin);
        bytes32 minterRole = passport.MINTER_ROLE();
        vm.prank(admin);
        passport.grantRole(minterRole, minter);
    }

    function test_issue_returnsTokenId() public {
        vm.prank(minter);
        uint256 id = passport.issue(user, "zeus", "governance", "1.0.0", "claude-opus-4-7");
        assertEq(id, 1);
    }

    function test_ownerOf_afterIssue() public {
        vm.prank(minter);
        passport.issue(user, "hermes", "messenger", "1.0.0", "claude-sonnet-4-6");
        assertEq(passport.ownerOf(1), user);
    }

    function test_meta_fields() public {
        vm.prank(minter);
        passport.issue(user, "apollo", "oracle", "2.0.0", "claude-haiku-4-5");
        AgentPassport.AgentMeta memory m = passport.getMeta(1);
        assertEq(m.name, "apollo");
        assertEq(m.role, "oracle");
        assertEq(m.version, "2.0.0");
        assertEq(m.modelId, "claude-haiku-4-5");
        assertGt(m.issuedAt, 0);
    }

    function test_passportOf_byName() public {
        vm.prank(minter);
        passport.issue(user, "athena", "strategy", "1.0.0", "claude-opus-4-7");
        assertEq(passport.passportOf("athena"), 1);
    }

    function test_passportOf_unknown_returnsZero() public view {
        assertEq(passport.passportOf("nobody"), 0);
    }

    function test_totalIssued() public {
        vm.startPrank(minter);
        passport.issue(user, "zeus", "governance", "1.0.0", "claude-opus-4-7");
        passport.issue(user2, "hermes", "messenger", "1.0.0", "claude-sonnet-4-6");
        vm.stopPrank();
        assertEq(passport.totalIssued(), 2);
    }

    function test_nameTaken_reverts() public {
        vm.startPrank(minter);
        passport.issue(user, "zeus", "governance", "1.0.0", "claude-opus-4-7");
        vm.expectRevert();
        passport.issue(user2, "zeus", "governance", "1.0.0", "claude-opus-4-7");
        vm.stopPrank();
    }

    function test_issue_revertsWithoutRole() public {
        vm.prank(user);
        vm.expectRevert();
        passport.issue(user, "imposter", "none", "1.0.0", "gpt-4");
    }

    function test_soulBound_transferReverts() public {
        vm.prank(minter);
        passport.issue(user, "zeus", "governance", "1.0.0", "claude-opus-4-7");
        vm.prank(user);
        vm.expectRevert();
        passport.transferFrom(user, user2, 1);
    }

    function test_supportsInterface_erc721() public view {
        assertTrue(passport.supportsInterface(type(IERC721).interfaceId));
    }
}
