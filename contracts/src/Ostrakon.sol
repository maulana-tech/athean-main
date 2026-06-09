// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Ostrakon
/// @notice On-chain scoring records for agent performance by period.
contract Ostrakon is AccessControl {
    bytes32 public constant SCORER_ROLE = keccak256("SCORER_ROLE");

    struct Score {
        string  agentName;
        string  period;          // e.g. "2026-W23"
        int256  deltaBps;        // score delta in basis points
        uint256 totalWins;
        uint256 totalLosses;
        uint256 recordedAt;
    }

    uint256 private _count;
    mapping(uint256 => Score) private _scores;

    event ScoreRecorded(
        uint256 indexed index,
        string  agentName,
        string  period,
        int256  deltaBps
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCORER_ROLE, admin);
    }

    function recordScore(
        string calldata agentName,
        string calldata period,
        int256 deltaBps,
        uint256 totalWins,
        uint256 totalLosses
    ) external onlyRole(SCORER_ROLE) returns (uint256 index) {
        index = _count++;
        _scores[index] = Score({
            agentName:   agentName,
            period:      period,
            deltaBps:    deltaBps,
            totalWins:   totalWins,
            totalLosses: totalLosses,
            recordedAt:  block.timestamp
        });
        emit ScoreRecorded(index, agentName, period, deltaBps);
    }

    function total() external view returns (uint256) { return _count; }

    function getScore(uint256 index) external view returns (Score memory) {
        require(index < _count, "out of range");
        return _scores[index];
    }
}
