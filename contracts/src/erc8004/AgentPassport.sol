// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title AgentPassport
/// @notice ERC-721 identity NFT for each Athean AI agent (ERC-8004 pattern).
///         One token per named agent. Immutable after minting — agents cannot
///         transfer their passport; it is soul-bound to the deployer address.
contract AgentPassport is ERC721, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    struct AgentMeta {
        string  name;
        string  role;
        string  version;
        string  modelId;    // e.g. "claude-opus-4-7"
        uint256 issuedAt;
    }

    uint256 private _nextTokenId;
    mapping(uint256 => AgentMeta) private _meta;
    mapping(string => uint256)    private _nameToId; // 0 = unregistered

    event PassportIssued(uint256 indexed tokenId, string name, string role, string modelId);

    constructor(address admin) ERC721("Athean Agent Passport", "PAP") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _nextTokenId = 1;
    }

    function issue(
        address to,
        string calldata name,
        string calldata role,
        string calldata version,
        string calldata modelId
    ) external onlyRole(MINTER_ROLE) returns (uint256 tokenId) {
        require(_nameToId[name] == 0, "name taken");
        tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
        _meta[tokenId] = AgentMeta({
            name:     name,
            role:     role,
            version:  version,
            modelId:  modelId,
            issuedAt: block.timestamp
        });
        _nameToId[name] = tokenId;
        emit PassportIssued(tokenId, name, role, modelId);
    }

    function getMeta(uint256 tokenId) external view returns (AgentMeta memory) {
        require(_ownerOf(tokenId) != address(0), "nonexistent");
        return _meta[tokenId];
    }

    function passportOf(string calldata name) external view returns (uint256) {
        return _nameToId[name];
    }

    function totalIssued() external view returns (uint256) {
        return _nextTokenId - 1;
    }

    // Soul-bound: block all transfers except minting (from == address(0)).
    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        address from = _ownerOf(tokenId);
        require(from == address(0), "soul-bound: non-transferable");
        return super._update(to, tokenId, auth);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
