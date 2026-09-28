/** Field definitions for the 39 model input features.
 *  Generated from data/processed/split_metadata.json -- names are exact.
 *  FLAG / Address / target / label are never model inputs and are not listed here.
 */
export type FieldKind = 'number' | 'token';

export interface ModelField {
  name: string;
  label: string;
  kind: FieldKind;
  section: string;
  help?: string;
}

export interface FieldSection { id: string; title: string; fields: ModelField[]; }

const CAT = new Set([' ERC20 most sent token type', ' ERC20_most_rec_token_type']);

function label(n: string): string {
  return n.trim().replace(/\s+/g, ' ');
}

const SECTIONS: Array<[string, string, string[]]> = [
  ['account', 'Account / activity information', [
    'Time Diff between first and last (Mins)',
    'total transactions (including tnx to create contract',
    'Number of Created Contracts',
    'Sent tnx',
    'Received Tnx',
    'Unique Received From Addresses',
    'Unique Sent To Addresses',
  ]],
  ['ethereum', 'Ethereum transaction behavior', [
    'total Ether sent',
    'total ether received',
    'total ether balance',
    'total ether sent contracts',
  ]],
  ['received', 'Received transaction behavior', [
    'min value received',
    'max value received ',
    'avg val received',
    'Avg min between received tnx',
  ]],
  ['sent', 'Sent transaction behavior', [
    'min val sent',
    'max val sent',
    'avg val sent',
    'Avg min between sent tnx',
    'min value sent to contract',
    'max val sent to contract',
    'avg value sent to contract',
  ]],
  ['erc20', 'ERC20 / token behavior', [
    ' Total ERC20 tnxs',
    ' ERC20 total Ether received',
    ' ERC20 total ether sent',
    ' ERC20 total Ether sent contract',
    ' ERC20 uniq sent addr',
    ' ERC20 uniq rec addr',
    ' ERC20 uniq rec contract addr',
    ' ERC20 min val rec',
    ' ERC20 max val rec',
    ' ERC20 avg val rec',
    ' ERC20 min val sent',
    ' ERC20 max val sent',
    ' ERC20 avg val sent',
    ' ERC20 uniq sent token name',
    ' ERC20 uniq rec token name',
  ]],
  ['tokentypes', 'Token type information', [
    ' ERC20 most sent token type',
    ' ERC20_most_rec_token_type',
  ]],
];

const HELP: Record<string, string> = {
  'Time Diff between first and last (Mins)': "Minutes between the account's first and last observed transaction.",
  'Unique Received From Addresses': "Distinct addresses that sent funds to this account. High counts are the model's strongest fraud association.",
  ' ERC20_most_rec_token_type': "Most frequently received ERC20 token type. Enter 'none' if the account has no ERC20 activity.",
  ' ERC20 most sent token type': "Most frequently sent ERC20 token type. Enter 'none' if the account has no ERC20 activity.",
};

export const FIELD_SECTIONS: FieldSection[] = SECTIONS.map(([id, title, names]) => ({
  id, title,
  fields: names.map((name) => ({
    name,
    label: label(name),
    kind: CAT.has(name) ? 'token' : 'number',
    section: id,
    help: HELP[name],
  })),
}));

export const ALL_FIELDS: ModelField[] = FIELD_SECTIONS.flatMap((s) => s.fields);
export const FIELD_NAMES: string[] = ALL_FIELDS.map((f) => f.name);
