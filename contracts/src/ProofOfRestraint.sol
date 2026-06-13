// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ProofOfRestraint
/// @notice Records every trade Areopagus declines on-chain.
/// @dev ABI is consumed by services/areopagus/src/areopagus/chain.py —
///      function signatures must not change without updating that file.
///      topics[1] of TradeDeclined carries the proofId as an indexed uint256
///      so the off-chain receipt parser can extract it from logs[0].topics[1].
contract ProofOfRestraint is AccessControl {
    bytes32 public constant RECORDER_ROLE = keccak256("RECORDER_ROLE");

    struct Proof {
        bytes32 signalHash;
        string marketId;
        string reasonCode;
        string note;
        uint256 timestamp;
        address recorder;
    }

    uint256 private _nextProofId;
    mapping(uint256 => Proof) private _proofs;

    event TradeDeclined(
        uint256 indexed proofId,
        bytes32 indexed signalHash,
        string marketId,
        string reasonCode,
        address recorder
    );

    constructor(
        address admin
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RECORDER_ROLE, admin);
        _nextProofId = 1;
    }

    /// @notice Record a declined trade. Returns the monotonic proof ID.
    function declineTrade(
        bytes32 signalHash,
        string calldata marketId,
        string calldata reasonCode,
        string calldata note
    ) external onlyRole(RECORDER_ROLE) returns (uint256 proofId) {
        proofId = _nextProofId++;
        _proofs[proofId] = Proof({
            signalHash: signalHash,
            marketId: marketId,
            reasonCode: reasonCode,
            note: note,
            timestamp: block.timestamp,
            recorder: msg.sender
        });
        emit TradeDeclined(proofId, signalHash, marketId, reasonCode, msg.sender);
    }

    /// @notice Next proof ID to be assigned. equals totalProofs + 1.
    function nextProofId() external view returns (uint256) {
        return _nextProofId;
    }

    function proof(
        uint256 proofId
    ) external view returns (Proof memory) {
        require(proofId > 0 && proofId < _nextProofId, "unknown proof");
        return _proofs[proofId];
    }

    function totalProofs() external view returns (uint256) {
        return _nextProofId - 1;
    }
}
