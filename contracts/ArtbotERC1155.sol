// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ArtbotERC1155
 * @notice Fully ERC-1155 and OpenSea compliant smart contract for artbot on Base.
 * Fixes the non-standard balanceOf argument order and implements all mandatory ERC-1155 functions.
 */
contract ArtbotERC1155 is ERC1155, Ownable {
    string public name = "artbot";
    string public symbol = "ARTBOT";

    // Individual token URIs
    mapping(uint256 => string) private _tokenURIs;
    // Track total supply per token ID
    mapping(uint256 => uint256) public totalSupply;

    constructor() ERC1155("") Ownable(msg.sender) {}

    /**
     * @notice Mint a new 1/1 artwork token
     * @param to The recipient address (typically the bot's address)
     * @param id The token ID (e.g. 20261012)
     * @param tokenURI The metadata URI (e.g. "https://therog1.github.io/artbotonbase/days/2026-10-12.json")
     */
    function mint(address to, uint256 id, string memory tokenURI) external onlyOwner {
        require(totalSupply[id] == 0, "Token already minted");
        _mint(to, id, 1, "");
        totalSupply[id] = 1;
        _tokenURIs[id] = tokenURI;
        emit URI(tokenURI, id);
    }

    /**
     * @notice Returns the metadata URI for a token ID
     * @dev Complies with ERC-1155 Metadata URI extension
     */
    function uri(uint256 id) public view override returns (string memory) {
        string memory customUri = _tokenURIs[id];
        if (bytes(customUri).length > 0) {
            return customUri;
        }
        return super.uri(id);
    }

    /**
     * @notice Set or update token URI if necessary
     */
    function setURI(uint256 id, string memory newUri) external onlyOwner {
        _tokenURIs[id] = newUri;
        emit URI(newUri, id);
    }

    /**
     * @notice Set contract collection name and symbol
     */
    function setCollectionInfo(string memory newName, string memory newSymbol) external onlyOwner {
        name = newName;
        symbol = newSymbol;
    }
}
