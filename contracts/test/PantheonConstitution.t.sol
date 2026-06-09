// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/PantheonConstitution.sol";

contract PantheonConstitutionTest is Test {
    PantheonConstitution constitution;

    string[] ids;
    string[] bodies;

    function setUp() public {
        ids.push(unicode"II §1");
        ids.push(unicode"IV §1");
        ids.push(unicode"VI §1");
        bodies.push("No position shall exceed five percent of total book equity.");
        bodies.push("No trade where 24-hour volume falls below fifty thousand USDC.");
        bodies.push("Kelly is taken at one-half. Never full. Never doubled.");
        constitution = new PantheonConstitution(ids, bodies);
    }

    function test_articleCount() public view {
        assertEq(constitution.articleCount(), 3);
    }

    function test_firstArticle() public view {
        (string memory id, string memory body) = constitution.article(0);
        assertEq(id,   unicode"II §1");
        assertEq(body, "No position shall exceed five percent of total book equity.");
    }

    function test_lastArticle() public view {
        (string memory id, string memory body) = constitution.article(2);
        assertEq(id,   unicode"VI §1");
        assertEq(body, "Kelly is taken at one-half. Never full. Never doubled.");
    }

    function test_outOfRange_reverts() public {
        vm.expectRevert();
        constitution.article(3);
    }

    function test_constitutionHash_nonzero() public view {
        assertNotEq(constitution.constitutionHash(), bytes32(0));
    }

    function test_constitutionHash_deterministic() public view {
        assertEq(constitution.constitutionHash(), constitution.constitutionHash());
    }

    function test_sealedAt_set() public view {
        assertGt(constitution.sealedAt(), 0);
    }

    function test_deployer_set() public view {
        assertEq(constitution.deployer(), address(this));
    }

    function test_version() public view {
        string memory ver = constitution.VERSION();
        assertEq(ver, "1.0.0");
    }

    function test_lengthMismatch_reverts() public {
        string[] memory badIds   = new string[](1);
        string[] memory badBodies = new string[](2);
        badIds[0]    = "X";
        badBodies[0] = "foo";
        badBodies[1] = "bar";
        vm.expectRevert();
        new PantheonConstitution(badIds, badBodies);
    }

    function test_emptyArray_reverts() public {
        string[] memory empty = new string[](0);
        vm.expectRevert();
        new PantheonConstitution(empty, empty);
    }
}
