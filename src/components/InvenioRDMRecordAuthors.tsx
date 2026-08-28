import React from 'react';

import type { InvenioRDMCreator } from '../api_calls';

type InvenioRDMRecordAuthorsProps = {
  creators?: InvenioRDMCreator[];
};

const RECORD_AUTHORS_LABEL = 'Record authors';

function creatorName(creator: InvenioRDMCreator): string {
  const personOrOrg = creator.person_or_org;
  return (
    personOrOrg.name ||
    [personOrOrg.given_name, personOrOrg.family_name]
      .filter(Boolean)
      .join(' ') ||
    'Unknown author'
  );
}

/** Displays a compact, wrapping list of a record's creator names. */
export const InvenioRDMRecordAuthors: React.FC<
  InvenioRDMRecordAuthorsProps
> = ({ creators }) => {
  if(!creators?.length) {
    return null;
  }

  return (
    <section
      aria-label={RECORD_AUTHORS_LABEL}
      className="mb-1 flex items-baseline gap-1 text-xs text-foreground-secondary"
    >
      <span className="shrink-0 font-semibold">
        {creators.length === 1 ? 'Author:' : 'Authors:'}
      </span>
      <span className="max-h-16 min-w-0 flex-1 overflow-y-auto leading-5">
        {creators.map((creator, index) => (
          <React.Fragment key={`${creatorName(creator)}:${index}`}>
            <span className="font-medium text-foreground">
              {creatorName(creator)}
            </span>
            {index < creators.length - 1 ? '; ' : null}
          </React.Fragment>
        ))}
      </span>
    </section>
  );
};
