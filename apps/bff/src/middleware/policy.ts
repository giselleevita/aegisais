import type { FastifyReply, FastifyRequest } from "fastify";
import type { ClassificationLevel } from "../types.js";

const CLASSIFICATION_ORDER: Record<ClassificationLevel, number> = {
  UNCLASSIFIED: 0,
  RESTRICTED: 1,
  CONFIDENTIAL: 2,
  SECRET: 3,
  TOP_SECRET: 4,
};

function highestClearance(clearances: ClassificationLevel[]): ClassificationLevel {
  if (clearances.length === 0) return "UNCLASSIFIED";
  return clearances.reduce((highest, current) => {
    return CLASSIFICATION_ORDER[current] > CLASSIFICATION_ORDER[highest] ? current : highest;
  }, "UNCLASSIFIED" as ClassificationLevel);
}

export function requireClassification(minLevel: ClassificationLevel) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const viewer = request.viewer;
    if (!viewer) {
      reply.code(401).send({ error: "Authentication required" });
      return;
    }

    const effective = highestClearance(viewer.clearances);
    if (CLASSIFICATION_ORDER[effective] < CLASSIFICATION_ORDER[minLevel]) {
      reply.code(403).send({
        error: "Insufficient classification clearance",
        required: minLevel,
        effective,
      });
      return;
    }
  };
}

export function requireReleasability(tag: string) {
  const requiredTag = tag.toUpperCase().trim();
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const viewer = request.viewer;
    if (!viewer) {
      reply.code(401).send({ error: "Authentication required" });
      return;
    }

    if (!viewer.releasability.includes(requiredTag)) {
      reply.code(403).send({
        error: "Insufficient releasability",
        required: requiredTag,
      });
      return;
    }
  };
}
