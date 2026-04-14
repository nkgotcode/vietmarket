# VietMarket Phase 9C Telegram Operator Workflows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn Phase 6 delivery and Phase 8 approvals into Telegram-first operator workflows with durable delivery records.

**Architecture:** Keep Postgres as the system of record by persisting delivery attempts in `delivery_events`, then let Telegram be the operator presentation layer. Support both real-send and dry-run modes so the workflow is verifiable even before production bot credentials are wired.

**Tech Stack:** Timescale/Postgres, Python supervisor scripts, Telegram Bot API over HTTPS, shell verification scripts.
