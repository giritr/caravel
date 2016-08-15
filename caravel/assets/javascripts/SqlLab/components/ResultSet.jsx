import React from 'react';
import { Alert, Button } from 'react-bootstrap';
import { Table } from 'reactable';

import VisualizeModal from './VisualizeModal';


class ResultSet extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      searchText: '',
      showModal: false,
    };
  }
  shouldComponentUpdate(nextProps, nextState) {
    return (
      this.state.searchText !== nextState.searchText ||
      this.state.showModal !== nextState.showModal
    );
  }
  changeSearch(event) {
    this.setState({ searchText: event.target.value });
  }
  showModal() {
    this.setState({ showModal: true });
  }
  hideModal() {
    this.setState({ showModal: false });
  }
  render() {
    const results = this.props.query.results;
    let controls = <div className="noControls" />;
    if (this.props.showControls) {
      controls = (
        <div className="ResultSetControls">
          <div className="clearfix">
            <div className="pull-left">
              <Button className="m-r-5" onClick={this.showModal.bind(this)}>
                <i className="fa fa-line-chart m-l-1" /> Visualize
              </Button>
              <Button className="m-r-5"><i className="fa fa-file-text-o" /> .CSV</Button>
            </div>
            <div className="pull-right">
              <input
                type="text"
                onChange={this.changeSearch.bind(this)}
                className="form-control"
                placeholder="Search Results"
              />
            </div>
          </div>
        </div>
      );
    }
    if (results.data.length > 0) {
      return (
        <div>
          <VisualizeModal
            show={this.state.showModal}
            query={this.props.query}
            onHide={this.hideModal.bind(this)}
          />
          {controls}
          <div className="ResultSet">
            <Table
              data={results.data}
              columns={results.columns}
              sortable
              className="table table-condensed table-bordered"
              filterBy={this.state.searchText}
              filterable={results.columns}
              hideFilterInput
            />
          </div>
        </div>
      );
    }
    return (<Alert bsStyle="warning">The query returned no data</Alert>);
  }
}
ResultSet.propTypes = {
  query: React.PropTypes.object,
  showControls: React.PropTypes.boolean,
  search: React.PropTypes.boolean,
  searchText: React.PropTypes.string,
};
ResultSet.defaultProps = {
  showControls: true,
  search: true,
  searchText: '',
};

export default ResultSet;
