import React from 'react';

import { InvenioRDMRecordAuthors } from './InvenioRDMRecordAuthors';

function textContent(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') {
    return String(node);
  }
  if (!React.isValidElement(node)) {
    return '';
  }

  const element = node as React.ReactElement<{ children?: React.ReactNode }>;
  return React.Children.toArray(element.props.children)
    .map(textContent)
    .join('');
}

describe('InvenioRDMRecordAuthors', () => {
  it('renders creator names in a compact semicolon-separated list', () => {
    const rendered = InvenioRDMRecordAuthors({
      creators: [
        {
          person_or_org: {
            type: 'personal',
            name: 'Lovelace, Ada'
          }
        },
        {
          person_or_org: {
            type: 'personal',
            given_name: 'Grace',
            family_name: 'Hopper'
          }
        }
      ]
    });

    expect(textContent(rendered)).toBe('Authors:Lovelace, Ada; Grace Hopper');
  });

  it('renders nothing when creators are unavailable', () => {
    expect(InvenioRDMRecordAuthors({})).toBeNull();
  });
});
