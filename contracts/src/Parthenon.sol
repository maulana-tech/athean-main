// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Parthenon
/// @notice Merkle-root anchoring contract for IPFS/Irys archive batches.
///         No direct IPFS calls from other services — route through here.
contract Parthenon is AccessControl {
    bytes32 public constant ANCHOR_ROLE = keccak256("ANCHOR_ROLE");

    struct Anchor {
        bytes32 merkleRoot;
        string  ipfsCid;
        string  label;       // e.g. "boule-traces-2026-06-09"
        uint256 anchoredAt;
        address anchoredBy;
    }

    uint256 private _count;
    mapping(uint256 => Anchor) private _anchors;
    mapping(bytes32 => uint256) private _rootToSlot; // 0 = absent, else index+1

    event RootAnchored(uint256 indexed index, bytes32 indexed merkleRoot, string label);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ANCHOR_ROLE, admin);
    }

    function anchorRoot(
        bytes32 merkleRoot,
        string calldata ipfsCid,
        string calldata label
    ) external onlyRole(ANCHOR_ROLE) returns (uint256 index) {
        require(_rootToSlot[merkleRoot] == 0, "root already anchored");
        index = _count++;
        _anchors[index] = Anchor({
            merkleRoot: merkleRoot,
            ipfsCid:    ipfsCid,
            label:      label,
            anchoredAt: block.timestamp,
            anchoredBy: msg.sender
        });
        _rootToSlot[merkleRoot] = index + 1;
        emit RootAnchored(index, merkleRoot, label);
    }

    function total() external view returns (uint256) { return _count; }

    function getAnchor(uint256 index) external view returns (Anchor memory) {
        require(index < _count, "out of range");
        return _anchors[index];
    }

    function indexByRoot(bytes32 root) external view returns (uint256) {
        uint256 slot = _rootToSlot[root];
        require(slot != 0, "not found");
        return slot - 1;
    }
}
