import React from 'react';

import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import * as Actions from '../actions';

import QueryTable from './QueryTable';
import { Alert } from 'react-bootstrap';

const QueryHistory = (props) => {
  const activeQeId = props.tabHistory[props.tabHistory.length - 1];
  const queries = props.queries.filter((q) => (q.sqlEditorId === activeQeId));
  if (queries.length > 0) {
    return (
      <QueryTable
        columns={['state', 'started', 'duration', 'rows', 'sql', 'actions']}
        queries={queries}
      />
    );
  }
  return (
    <Alert bsStyle="info">
      No query history yet...
    </Alert>
  );
};

QueryHistory.defaultProps = {
  queries: [],
};

QueryHistory.propTypes = {
  queries: React.PropTypes.array,
  tabHistory: React.PropTypes.array,
  actions: React.PropTypes.object,
};

function mapStateToProps(state) {
  return {
    queries: state.queries,
    tabHistory: state.tabHistory,
  };
}
function mapDispatchToProps(dispatch) {
  return {
    actions: bindActionCreators(Actions, dispatch),
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(QueryHistory);
