// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title NoTradeAlpha
/// @notice Tracks counterfactual PnL for every declined trade.
///         Each record links back to a ProofOfRestraint proofId and is
///         resolved once the market settles.
contract NoTradeAlpha is AccessControl {
    bytes32 public constant RECORDER_ROLE = keccak256("RECORDER_ROLE");
    bytes32 public constant RESOLVER_ROLE = keccak256("RESOLVER_ROLE");

    enum Outcome { PENDING, WIN, LOSS, VOID }

    struct CounterfactualRecord {
        uint256 proofId;
        bytes32 signalHash;
        string  marketId;
        int256  impliedEdgeBps;
        uint256 recordedAt;
        Outcome outcome;
        int256  counterfactualPnlBps;
        uint256 resolvedAt;
    }

    uint256 private _count;
    mapping(uint256 => CounterfactualRecord) private _records;
    mapping(uint256 => uint256) private _proofToSlot; // proofId → slot (0 = absent, else index+1)

    event RecordCreated(uint256 indexed index, uint256 indexed proofId, bytes32 signalHash);
    event RecordResolved(uint256 indexed index, Outcome outcome, int256 pnlBps);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RECORDER_ROLE, admin);
        _grantRole(RESOLVER_ROLE, admin);
    }

    function record(
        uint256 proofId,
        bytes32 signalHash,
        string calldata marketId,
        int256 impliedEdgeBps
    ) external onlyRole(RECORDER_ROLE) returns (uint256 index) {
        require(_proofToSlot[proofId] == 0, "proof already recorded");
        index = _count++;
        _records[index] = CounterfactualRecord({
            proofId:              proofId,
            signalHash:           signalHash,
            marketId:             marketId,
            impliedEdgeBps:       impliedEdgeBps,
            recordedAt:           block.timestamp,
            outcome:              Outcome.PENDING,
            counterfactualPnlBps: 0,
            resolvedAt:           0
        });
        _proofToSlot[proofId] = index + 1;
        emit RecordCreated(index, proofId, signalHash);
    }

    function resolve(
        uint256 index,
        Outcome outcome,
        int256 pnlBps
    ) external onlyRole(RESOLVER_ROLE) {
        require(index < _count, "out of range");
        CounterfactualRecord storage r = _records[index];
        require(r.outcome == Outcome.PENDING, "already resolved");
        r.outcome              = outcome;
        r.counterfactualPnlBps = pnlBps;
        r.resolvedAt           = block.timestamp;
        emit RecordResolved(index, outcome, pnlBps);
    }

    function total() external view returns (uint256) { return _count; }

    function getRecord(uint256 index) external view returns (CounterfactualRecord memory) {
        require(index < _count, "out of range");
        return _records[index];
    }

    function indexByProof(uint256 proofId) external view returns (uint256) {
        uint256 slot = _proofToSlot[proofId];
        require(slot != 0, "not found");
        return slot - 1;
    }
}
