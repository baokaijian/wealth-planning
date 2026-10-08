import { readFileSync } from 'node:fs';
import { assessFamily } from '../../src/utils/familyAssessment.js';

const input = JSON.parse(readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(assessFamily(input)));
