// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title SignalRegistry
/// @notice Append-only registry of Pythia signals with their band and edge.
contract SignalRegistry is AccessControl {
    bytes32 public constant WRITER_ROLE = keccak256("WRITER_ROLE");

    struct Signal {
        bytes32 signalHash;
        string signalId;
        string marketId;
        string band; // STRONG_YES / YES / PASS / NO / STRONG_NO
        int256 edgeBps; // expected value in basis points, signed
        uint256 createdAt;
        address emitter;
    }

    uint256 private _count;
    mapping(uint256 => Signal) private _signals;
    mapping(bytes32 => uint256) private _hashToSlot; // 0 = absent, else index+1

    event SignalEmitted(
        uint256 indexed index, bytes32 indexed signalHash, string signalId, string band
    );

    constructor(
        address admin
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(WRITER_ROLE, admin);
    }

    function recordSignal(
        bytes32 signalHash,
        string calldata signalId,
        string calldata marketId,
        string calldata band,
        int256 edgeBps
    ) external onlyRole(WRITER_ROLE) returns (uint256 index) {
        require(_hashToSlot[signalHash] == 0, "duplicate hash");
        index = _count++;
        _signals[index] = Signal({
            signalHash: signalHash,
            signalId: signalId,
            marketId: marketId,
            band: band,
            edgeBps: edgeBps,
            createdAt: block.timestamp,
            emitter: msg.sender
        });
        _hashToSlot[signalHash] = index + 1;
        emit SignalEmitted(index, signalHash, signalId, band);
    }

    function total() external view returns (uint256) {
        return _count;
    }

    function signal(
        uint256 index
    ) external view returns (Signal memory) {
        require(index < _count, "out of range");
        return _signals[index];
    }

    function indexByHash(
        bytes32 signalHash
    ) external view returns (uint256) {
        uint256 slot = _hashToSlot[signalHash];
        require(slot != 0, "not found");
        return slot - 1;
    }
}
