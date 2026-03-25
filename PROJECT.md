# CryptoScholar

**Type:** MCP server (open-source)
**Status:** Active development
**License:** MIT

## Problem
Crypto traders using Claude have no native way to run technical analysis on coins directly within their AI workflow. Switching between TradingView, CoinGecko, and Claude breaks context.

## Solution
A stateless MCP server that exposes 3 tools — analyze, rank, debate — directly in Claude. Fetches live data from CoinGecko free API. No signup, no DB, no infra required.

## Users
- Claude Code and Claude.ai users who trade or research crypto
- Developers building AI-powered crypto tools

## Goals
- analyze_coin: full TA snapshot (EMAs, RSI, MACD, ATR, BB, HV, regime, TSS)
- rank_coins: TSS-based comparative ranking across a list of symbols
- debate: Claude-generated bull/bear synthesis grounded in real TA data

## Non-Goals
- Portfolio tracking
- Trade execution
- Real-time streaming data
- Paid API data sources

## Stack
- Python 3.11+
- MCP SDK (FastMCP)
- pandas + pandas-ta for TA
- anthropic SDK for debate tool
- CoinGecko free API (no auth)

## OSS Application
Submitted to Anthropic Claude for OSS program — uses Claude API for debate synthesis tool.
