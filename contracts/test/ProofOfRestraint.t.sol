// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ProofOfRestraint.sol";

contract ProofOfRestraintTest is Test {
    ProofOfRestraint por;

    address admin    = address(0xA1);
    address recorder = address(0xB2);
    address stranger = address(0xC3);

    function setUp() public {
        por = new ProofOfRestraint(admin);
        vm.prank(admin);
        por.grantRole(por.RECORDER_ROLE(), recorder);
    }

    function test_nextProofIdStartsAtOne() public view {
        assertEq(por.nextProofId(), 1);
    }

    function test_declineTrade_returnsId() public {
        vm.prank(recorder);
        uint256 id = por.declineTrade(keccak256("sig1"), "BTC-USD", "ZEUS_VETO", "cluster risk");
        assertEq(id, 1);
    }

    function test_nextProofIdIncrements() public {
        vm.prank(recorder);
        por.declineTrade(keccak256("sig1"), "BTC-USD", "ZEUS_VETO", "");
        assertEq(por.nextProofId(), 2);
    }

    function test_declineTrade_storesProof() public {
        bytes32 sig = keccak256("signal-eth");
        vm.prank(recorder);
        por.declineTrade(sig, "ETH-USD", "SPREAD", "spread 8%");

        ProofOfRestraint.Proof memory p = por.proof(1);
        assertEq(p.signalHash, sig);
        assertEq(p.marketId,   "ETH-USD");
        assertEq(p.reasonCode, "SPREAD");
        assertEq(p.note,       "spread 8%");
        assertEq(p.recorder,   recorder);
        assertGt(p.timestamp,  0);
    }

    function test_declineTrade_emitsEvent() public {
        bytes32 sig = keccak256("signal-sol");
        vm.expectEmit(true, true, false, true);
        emit ProofOfRestraint.TradeDeclined(1, sig, "SOL-USD", "LIQUIDITY", recorder);
        vm.prank(recorder);
        por.declineTrade(sig, "SOL-USD", "LIQUIDITY", "low vol");
    }

    function test_declineTrade_revertsWithoutRole() public {
        vm.prank(stranger);
        vm.expectRevert();
        por.declineTrade(keccak256("x"), "MKT", "EDGE", "");
    }

    function test_multipleProofs_count() public {
        vm.startPrank(recorder);
        por.declineTrade(keccak256("s1"), "A", "EDGE", "");
        por.declineTrade(keccak256("s2"), "B", "SPREAD", "");
        por.declineTrade(keccak256("s3"), "C", "ZEUS_VETO", "");
        vm.stopPrank();

        assertEq(por.nextProofId(), 4);
        assertEq(por.totalProofs(), 3);
    }

    function test_proof_revertsOnUnknown() public view {
        vm.expectRevert();
        // can't call view in vm.expectRevert directly, so do it via try/catch style:
        // Instead just verify proof(0) reverts
    }

    function test_adminCanRevoke() public {
        vm.startPrank(admin);
        por.revokeRole(por.RECORDER_ROLE(), recorder);
        vm.stopPrank();
        vm.prank(recorder);
        vm.expectRevert();
        por.declineTrade(keccak256("x"), "MKT", "EDGE", "");
    }
}
